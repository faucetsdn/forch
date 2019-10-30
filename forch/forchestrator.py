"""Orchestrator component for controlling a Faucet SDN"""

from datetime import datetime
import logging
import os
import time
import yaml

import forch.constants as constants
import forch.faucet_event_client
import forch.http_server

from forch.cpn_state_collector import CPNStateCollector
from forch.faucet_state_collector import FaucetStateCollector
from forch.local_state_collector import LocalStateCollector

LOGGER = logging.getLogger('forch')


_FCONFIG_DEFAULT = 'forch.yaml'
_DEFAULT_PORT = 9019

class Forchestrator:
    """Main class encompassing faucet orchestrator components for dynamically
    controlling faucet ACLs at runtime"""

    _DETAIL_FORMAT = '%s is %s: %s'

    def __init__(self, config):
        self._config = config
        self._faucet_events = None
        self._server = None
        self._start_time = datetime.fromtimestamp(time.time()).isoformat()
        self._faucet_collector = FaucetStateCollector()
        self._local_collector = LocalStateCollector(config.get('process'))
        self._cpn_collector = CPNStateCollector()

    def initialize(self):
        """Initialize forchestrator instance"""
        LOGGER.info('Attaching event channel...')
        self._faucet_events = forch.faucet_event_client.FaucetEventClient(
            self._config.get('event_client', {}))
        self._faucet_events.connect()
        self._local_collector.initialize()
        self._cpn_collector.initialize()
        LOGGER.info('Using peer controller %s', self._get_peer_controller_url())

    def main_loop(self):
        """Main event processing loop"""
        LOGGER.info('Entering main event loop...')
        try:
            while self._handle_faucet_events():
                pass
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
            (stack_root, graph, dps) = self._faucet_events.as_stack_topo_change(event)
            if stack_root is not None:
                LOGGER.debug('stack dataplane_state change root:%s', stack_root)
                self._faucet_collector.process_stack_topo_change(timestamp, stack_root, graph, dps)
            (name, port, active) = self._faucet_events.as_lag_status(event)
            if name and port:
                LOGGER.debug('LAG state %s %s %s', name, port, active)
                self._faucet_collector.process_lag_state(timestamp, name, port, active)
            (name, connected) = self._faucet_events.as_dp_change(event)
            if name:
                LOGGER.debug('DP %s connected %r', name, connected)
                self._faucet_collector.process_dp_change(timestamp, name, connected)
        return False

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

    def _get_peer_controller_info(self):
        name = self._get_controller_name()
        controllers = self._config.get('site', {}).get('controllers', {})
        if name not in controllers:
            return (f'missing_controller_name_{name}', _DEFAULT_PORT)
        if len(controllers) != 2:
            return ('num_controllers_%s' % len(controllers), _DEFAULT_PORT)
        things = set(controllers.keys())
        things.remove(name)
        peer = list(things)[0]
        return self._get_controller_info(peer)

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
            'controller_name': self._get_controller_name()
        }
        overview.update(self._distill_summary(system_summary))
        return overview

    def _distill_summary(self, summaries):
        try:
            start_time = self._start_time
            summary_values = summaries.values()
            change_counts = list(map(lambda subsystem:
                                     subsystem.get('change_count', 0), summary_values))
            last_changes = list(map(lambda subsystem:
                                    subsystem.get('last_change', start_time), summary_values))
            last_updates = list(map(lambda subsystem:
                                    subsystem.get('last_update', start_time), summary_values))
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

        vrrp_state = self._local_collector.get_vrrp_state()
        if not vrrp_state.get('is_master'):
            detail = 'This controller is inactive. Please view peer controller.'
            return constants.STATE_INACTIVE, detail
        if has_error:
            return constants.STATE_BROKEN, detail
        if has_warning:
            return constants.STATE_DAMAGED, detail
        return constants.STATE_HEALTHY, detail

    def _get_system_summary(self, path):
        states = {
            'cpn_state': self._cpn_collector.get_cpn_summary(),
            'process_state': self._local_collector.get_process_summary(),
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
        reply['system_state_url'] = url

    def get_switch_state(self, path, params):
        """Get the state of the switches"""
        switch = params.get('switch')
        port = params.get('port')
        reply = self._faucet_collector.get_switch_state(switch, port)
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


def load_config():
    """Load configuration from the configuration file"""
    config_root = os.getenv('FORCH_CONFIG_DIR', '.')
    config_path = os.path.join(config_root, _FCONFIG_DEFAULT)
    LOGGER.info('Reading config file %s', os.path.abspath(config_path))
    with open(config_path, 'r') as stream:
        return yaml.safe_load(stream)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    CONFIG = load_config()
    FORCH = Forchestrator(CONFIG)
    FORCH.initialize()
    HTTP = forch.http_server.HttpServer(CONFIG.get('http', {}),
                                        FORCH.get_local_port())
    HTTP.map_request('system_state', FORCH.get_system_state)
    HTTP.map_request('dataplane_state', FORCH.get_dataplane_state)
    HTTP.map_request('switch_state', FORCH.get_switch_state)
    HTTP.map_request('cpn_state', FORCH.get_cpn_state)
    HTTP.map_request('process_state', FORCH.get_process_state)
    HTTP.map_request('host_path', FORCH.get_host_path)
    HTTP.map_request('list_hosts', FORCH.get_list_hosts)
    HTTP.map_request('', HTTP.static_file(''))
    HTTP.start_server()
    FORCH.main_loop()
    LOGGER.warning('Exiting program')
    HTTP.stop_server()
