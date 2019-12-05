"""Orchestrator component for controlling a Faucet SDN"""

from datetime import datetime
import functools
import logging
import os
import sys
import threading
import time
import yaml

from google.protobuf.message import Message

import forch.constants as constants
import forch.faucet_event_client
import forch.http_server
from forch.utils import proto_dict

from forch.cpn_state_collector import CPNStateCollector
from forch.faucet_state_collector import FaucetStateCollector
from forch.local_state_collector import LocalStateCollector
from forch.varz_state_collector import VarzStateCollector

LOGGER = logging.getLogger('forch')

_FORCH_CONFIG_DEFAULT = 'forch.yaml'
_FAUCET_CONFIG_DEFAULT = 'faucet.yaml'
_DEFAULT_PORT = 9019
_PROMETHEUS_HOST = '127.0.0.1'
_LOG_FORMAT = '%(asctime)s %(name)-8s %(levelname)-8s %(message)s'
_LOG_DATE_FORMAT = '%b %d %H:%M:%S'

class Forchestrator:
    """Main class encompassing faucet orchestrator components for dynamically
    controlling faucet ACLs at runtime"""

    _DETAIL_FORMAT = '%s is %s: %s'

    def __init__(self, config):
        self._config = config
        self._faucet_config_file = None
        self._faucet_events = None
        self._start_time = datetime.fromtimestamp(time.time()).isoformat()

        self._faucet_collector = None
        self._varz_collector = None
        self._local_collector = None
        self._cpn_collector = None
        self._initialized = False
        self._is_active = False
        self._active_state_lock = threading.Lock()
        self._event_horizon = 0

    def initialize(self):
        """Initialize forchestrator instance"""
        self._faucet_collector = FaucetStateCollector()
        self._local_collector = LocalStateCollector(
            self._config.get('process'), self.cleanup, self.handle_active_state)
        self._cpn_collector = CPNStateCollector()

        self._faucet_config_file = os.path.join(
            os.getenv('FAUCET_CONFIG_DIR'), _FAUCET_CONFIG_DEFAULT)
        if not self._faucet_config_file or not os.path.exists(self._faucet_config_file):
            raise Exception(f"Faucet config file does not exist: {self._faucet_config_file}")

        prom_port = os.getenv('PROMETHEUS_PORT')
        if not prom_port:
            raise Exception("PROMETHEUS_PORT is not set")
        prom_url = f"http://{_PROMETHEUS_HOST}:{prom_port}"
        self._varz_collector = VarzStateCollector(prom_url)

        LOGGER.info('Attaching event channel...')
        self._faucet_events = forch.faucet_event_client.FaucetEventClient(
            self._config.get('event_client', {}))
        self._local_collector.initialize()
        self._cpn_collector.initialize()
        LOGGER.info('Using peer controller %s', self._get_peer_controller_url())
        self._initialized = True

    def initialized(self):
        """If forch is initialized or not"""
        return self._initialized

    def _restore_states(self):
        # Make sure the event socket is connected so there's no loss of information.
        assert self._faucet_events.event_socket_connected, 'restore states without connection'
        metrics = self._varz_collector.get_metrics()
        self._event_horizon = self._faucet_collector.restore_states_from_metrics(metrics)
        LOGGER.info('Setting event horizon to event #%d', self._event_horizon)

        current_time = time.time()
        faucet_config = self._get_faucet_config()
        self._faucet_collector.process_dataplane_config_change(
            current_time, faucet_config.get('dps', {}))

    def main_loop(self):
        """Main event processing loop"""
        LOGGER.info('Entering main event loop...')
        try:
            while self._handle_faucet_events():
                while not self._faucet_events.event_socket_connected:
                    LOGGER.info('Attempting faucet event sock connection...')
                    time.sleep(1)
                    try:
                        self._faucet_events.connect()
                        self._restore_states()
                        self._faucet_collector.set_state_restored(True)
                    except Exception as e:
                        LOGGER.error("Cannot restore states or connect to faucet: %s", e)
                        self._faucet_collector.set_state_restored(False, e)
        except KeyboardInterrupt:
            LOGGER.info('Keyboard interrupt. Exiting.')
            self._faucet_events.disconnect()
        except Exception as e:
            LOGGER.error("Exception: %s", e)
            raise

    # TODO: This should likely be moved into the faucet_state_collector.
    # pylint: disable=too-many-locals
    def _handle_faucet_events(self):
        while self._faucet_events:
            event = self._faucet_events.next_event(blocking=True)
            if not event:
                return True
            try:
                self._handle_faucet_event(event)
            except Exception as e:
                LOGGER.warning('While processing event %s', event)
                raise e
        return False

    def _handle_faucet_event(self, event):
        # TODO: Move this down into some other class so 'event_id' isn't exposed in forchestrator.
        if int(event.get('event_id')) < self._event_horizon:
            LOGGER.debug('Outdated faucet event #%d', event.get('event_id'))
            # TODO: Actually flush event (no-op) when varz sufficient.

        timestamp = event.get("time")
        LOGGER.debug("Event: %r", event)
        (name, dpid, port, active) = self._faucet_events.as_port_state(event)
        if dpid and port:
            LOGGER.debug('Port state %s %s %s', name, port, active)
            self._faucet_collector.process_port_state(timestamp, name, port, active)

        (name, dpid, port, target_mac, src_ip) = self._faucet_events.as_port_learn(event)
        if dpid and port:
            LOGGER.debug('Port learn %s %s %s', name, port, target_mac)
            self._faucet_collector.process_port_learn(timestamp, name, port, target_mac, src_ip)

        (name, dpid, restart_type, dps_config) = self._faucet_events.as_config_change(event)
        if dpid is not None:
            LOGGER.debug('DP restart %s %s', name, restart_type)
            self._faucet_collector.process_dp_config_change(timestamp, name, restart_type, dpid)
        if dps_config:
            LOGGER.debug('Config change. New config: %s', dps_config)
            self._faucet_collector.process_dataplane_config_change(timestamp, dps_config)

        topo_change = self._faucet_events.as_stack_topo_change(event)
        if topo_change:
            LOGGER.debug('stack dataplane_state change root:%s', topo_change.stack_root)
            self._faucet_collector.process_stack_topo_change(topo_change)

        (name, port, state) = self._faucet_events.as_stack_state(event)
        if name is not None:
            LOGGER.debug('stack stack_state change: %s:%d, %d', name, port, state)
            self._faucet_collector.process_stack_state(timestamp, name, port, state)

        (name, port, state) = self._faucet_events.as_lag_state(event)
        if name and port:
            LOGGER.debug('LAG state %s %s %s', name, port, state)
            self._faucet_collector.process_lag_state(timestamp, name, port, state)

        (name, connected) = self._faucet_events.as_dp_change(event)
        if name:
            LOGGER.debug('DP %s connected %r', name, connected)
            self._faucet_collector.process_dp_change(timestamp, name, None, connected)

    def _get_controller_info(self, target):
        controllers = self._config.get('site', {}).get('controllers', {})
        if target not in controllers:
            return (f'missing_target_{target}', _DEFAULT_PORT)
        controller = controllers[target]
        controller = controller if controller else {}
        port = controller.get('port', _DEFAULT_PORT)
        host = controller.get('fqdn', target)
        return (host, port)

    def get_local_port(self):
        """Get the local port for this instance"""
        info = self._get_controller_info(self._get_controller_name())
        LOGGER.info('Local controller is at %s on %s', info[0], info[1])
        return int(info[1])

    def _make_controller_url(self, info):
        return f'http://{info[0]}:{info[1]}'

    def _get_local_controller_url(self):
        return self._make_controller_url(self._get_controller_info(self._get_controller_name()))

    def _get_peer_controller_name(self):
        name = self._get_controller_name()
        controllers = self._config.get('site', {}).get('controllers', {})
        if name not in controllers:
            return (f'missing_controller_name_{name}', _DEFAULT_PORT)
        if len(controllers) != 2:
            return ('num_controllers_%s' % len(controllers), _DEFAULT_PORT)
        things = set(controllers.keys())
        things.remove(name)
        return list(things)[0]

    def _get_peer_controller_info(self):
        return self._get_controller_info(self._get_peer_controller_name())

    def _get_peer_controller_url(self):
        return self._make_controller_url(self._get_peer_controller_info())

    def _get_controller_name(self):
        return os.getenv('CONTROLLER_NAME')

    def get_system_state(self, path, params):
        """Get an overview of the system state"""
        system_summary = self._get_system_summary(path)
        overview = {
            'peer_controller_url': self._get_peer_controller_url(),
            'summary_sources': system_summary,
            'site_name': self._config.get('site', {}).get('name', 'unknown'),
            'controller_name': self._get_controller_name(),
        }
        overview.update(self._distill_summary(system_summary))
        return overview

    def _distill_summary(self, summaries):
        try:
            start_time = self._start_time
            summary_values = summaries.values()
            change_counts = list(map(lambda subsystem:
                                     subsystem.get('change_count') or 0, summary_values))
            last_changes = list(map(lambda subsystem:
                                    subsystem.get('last_change') or start_time, summary_values))
            last_updates = list(map(lambda subsystem:
                                    subsystem.get('last_update') or start_time, summary_values))
            summary, detail = self._get_combined_summary(summaries)
            system_summary = {
                'system_state': summary,
                'system_state_detail': detail,
                'system_state_change_count': sum(change_counts),
                'system_state_last_change': max(last_changes),
                'system_state_last_update': max(last_updates)
            }
        except Exception as e:
            system_summary = {
                'system_state': 'error',
                'system_state_detail': str(e)
            }
            LOGGER.exception('Calculating state summary')
        return system_summary

    def _get_combined_summary(self, summary):
        controller_state, controller_state_detail = self._get_controller_state()
        if not controller_state == constants.STATE_ACTIVE:
            return controller_state, controller_state_detail

        has_error = False
        has_warning = False
        details = []
        for subsystem_name in summary:
            subsystem = summary[subsystem_name]
            state = subsystem.get('state', constants.STATE_BROKEN)
            if state in (constants.STATE_DOWN, constants.STATE_BROKEN):
                has_error = True
                details.append(subsystem_name)
            elif state != constants.STATE_HEALTHY:
                has_warning = True
                details.append(subsystem_name)
        if details:
            detail = 'broken subsystems: ' + ', '.join(details)
        else:
            detail = 'n/a'

        if not self._faucet_events.event_socket_connected:
            has_error = True
            detail += '. Faucet disconnected.'

        if has_error:
            return constants.STATE_BROKEN, detail
        if has_warning:
            return constants.STATE_DAMAGED, detail
        return constants.STATE_HEALTHY, detail

    def _get_system_summary(self, path):
        states = {
            'cpn_state': proto_dict(self._cpn_collector.get_cpn_summary()),
            'process_state': proto_dict(self._local_collector.get_process_summary()),
            'dataplane_state': self._faucet_collector.get_dataplane_summary(),
            'switch_state': self._faucet_collector.get_switch_summary(),
            'list_hosts': self._faucet_collector.get_host_summary()
        }
        url_base = self._extract_url_base(path)
        for state in states:
            summary = states[state]
            summary['url'] = f'{url_base}/?{state}'
        return states

    def _extract_url_base(self, path):
        slash = path.find('/')
        host = path[:slash]
        return f'http://{host}'

    def _augment_state_reply(self, reply, path):
        url = self._extract_url_base(path)
        if isinstance(reply, Message):
            reply.system_state_url = url
        else:
            reply['system_state_url'] = url

    def _get_controller_state(self):
        with self._active_state_lock:
            if not self._is_active:
                detail = 'This controller is inactive. Please view peer controller.'
                return constants.STATE_INACTIVE, detail

        cpn_state = self._cpn_collector.get_cpn_state()
        peer_controller = self._get_peer_controller_name()
        cpn_nodes = proto_dict(cpn_state).get('cpn_nodes')
        peer_controller_state = cpn_nodes.get(peer_controller, {}).get('state')

        if not peer_controller_state:
            LOGGER.error('Cannot get peer controller state: %s', peer_controller)

        if cpn_state.cpn_state == constants.STATE_INITIALIZING:
            detail = 'Initializing'
            return constants.STATE_INITIALIZING, detail

        if not peer_controller_state == constants.STATE_HEALTHY:
            detail = 'Lost reachability to peer controller.'
            return constants.STATE_SPLIT, detail

        return constants.STATE_ACTIVE, ''

    def _get_faucet_config(self):
        try:
            with open(self._faucet_config_file) as config_file:
                return yaml.safe_load(config_file)
        except Exception as e:
            LOGGER.error("Cannot read faucet config: %s", e)
            raise e

    def cleanup(self):
        """Clean up relevant internal data in all collectors"""
        self._faucet_collector.cleanup()

    def handle_active_state(self, is_master):
        """Handler for local state collector to handle vrrp state"""
        with self._active_state_lock:
            self._is_active = is_master
        self._faucet_collector.set_active(is_master)

    def get_switch_state(self, path, params):
        """Get the state of the switches"""
        switch = params.get('switch')
        port = params.get('port')
        host = self._extract_url_base(path)
        reply = self._faucet_collector.get_switch_state(switch, port, host)
        self._augment_state_reply(reply, path)
        return reply

    def get_dataplane_state(self, path, params):
        """Get the dataplane state overview"""
        reply = self._faucet_collector.get_dataplane_state()
        self._augment_state_reply(reply, path)
        return reply

    def get_host_path(self, path, params):
        """Get active host path"""
        eth_src = params.get('eth_src')
        eth_dst = params.get('eth_dst')
        to_egress = params.get('to_egress') == 'true'
        reply = self._faucet_collector.get_host_path(eth_src, eth_dst, to_egress)
        self._augment_state_reply(reply, path)
        return reply

    def get_list_hosts(self, path, params):
        """List learned access devices"""
        eth_src = params.get('eth_src')
        host = self._extract_url_base(path)
        reply = self._faucet_collector.get_list_hosts(host, eth_src)
        self._augment_state_reply(reply, path)
        return reply

    def get_cpn_state(self, path, params):
        """Get CPN state"""
        reply = self._cpn_collector.get_cpn_state()
        self._augment_state_reply(reply, path)
        return reply

    def get_process_state(self, path, params):
        """Get certain processes state on the controller machine"""
        reply = self._local_collector.get_process_state()
        self._augment_state_reply(reply, path)
        return reply

    def get_faucet_config(self, path, params):
        """Get faucet config from facuet config file"""
        try:
            reply = self._get_faucet_config()
            self._augment_state_reply(reply, path)
            return reply
        except Exception as e:
            return f"Cannot read faucet config: {e}"


def load_config():
    """Load configuration from the configuration file"""
    config_root = os.getenv('FORCH_CONFIG_DIR', '.')
    config_path = os.path.join(config_root, _FORCH_CONFIG_DEFAULT)
    LOGGER.info('Reading config file %s', os.path.abspath(config_path))
    try:
        with open(config_path, 'r') as stream:
            return yaml.safe_load(stream)
    except Exception as e:
        LOGGER.error('Cannot load config: %s', e)
        return None


def show_error(error, path, params):
    """Display errors"""
    return f"Cannot initialize forch: {str(error)}"


def get_log_path():
    """Get path for logging"""
    forch_log_dir = os.getenv('FORCH_LOG_DIR')
    if not forch_log_dir:
        return None
    return os.path.join(forch_log_dir, 'forch.log')


if __name__ == '__main__':
    logging.basicConfig(filename=get_log_path(),
                        format=_LOG_FORMAT,
                        datefmt=_LOG_DATE_FORMAT,
                        level=logging.INFO)
    CONFIG = load_config()
    if not CONFIG:
        LOGGER.error('Invalid config, exiting.')
        sys.exit(1)

    FORCH = Forchestrator(CONFIG)
    HTTP = forch.http_server.HttpServer(CONFIG.get('http', {}), FORCH.get_local_port())

    try:
        FORCH.initialize()
        HTTP.map_request('system_state', FORCH.get_system_state)
        HTTP.map_request('dataplane_state', FORCH.get_dataplane_state)
        HTTP.map_request('switch_state', FORCH.get_switch_state)
        HTTP.map_request('cpn_state', FORCH.get_cpn_state)
        HTTP.map_request('process_state', FORCH.get_process_state)
        HTTP.map_request('host_path', FORCH.get_host_path)
        HTTP.map_request('list_hosts', FORCH.get_list_hosts)
        HTTP.map_request('faucet_config', FORCH.get_faucet_config)
        HTTP.map_request('', HTTP.static_file(''))
    except Exception as e:
        LOGGER.error("Cannot initialize forch: %s", e)
        HTTP.map_request('', functools.partial(show_error, e))
    finally:
        HTTP.start_server()

    if FORCH.initialized():
        FORCH.main_loop()
    else:
        try:
            HTTP.join_thread()
        except KeyboardInterrupt:
            LOGGER.info('Keyboard interrupt. Exiting.')

    LOGGER.warning('Exiting program')
    HTTP.stop_server()
