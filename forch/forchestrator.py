"""Orchestrator component for controlling a Faucet SDN"""

from datetime import datetime
import logging
import os
import time
import sys
import yaml

import forch.faucet_event_client
import forch.http_server

from forch.cpn_state_collector import CPNStateCollector
from forch.faucet_state_collector import FaucetStateCollector
from forch.local_state_collector import LocalStateCollector

LOGGER = logging.getLogger('forch')


_FCONFIG_DEFAULT = 'forch.yaml'

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
        self._local_collector = LocalStateCollector()
        self._cpn_collector = CPNStateCollector()

    def initialize(self):
        """Initialize forchestrator instance"""
        LOGGER.info('Attaching event channel...')
        self._faucet_events = forch.faucet_event_client.FaucetEventClient(
            self._config.get('event_client', {}))
        self._faucet_events.connect()

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
    def _handle_faucet_events(self):
        while self._faucet_events:
            event = self._faucet_events.next_event()
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

    def _get_peer_controller_url(self):
        return 'http://google.com'

    def get_system_state(self, path, params):
        """Get an overview of the system state"""
        # TODO: These are all placeholder values, so need to be replaced.
        state_summary = self._get_state_summary()
        overview = {
            'peer_controller_url': self._get_peer_controller_url(),
            'state_summary_sources': state_summary,
            'site_name': self._config['site']['name'],
            'controller_hostname': os.getenv('HOSTNAME')
        }
        overview.update(self._distill_summary(state_summary))
        return overview

    def _distill_summary(self, summary):
        try:
            state_summary = {
                'state_summary': 'monkey'
            }
            start_time = self._start_time
            change_counts = list(map(lambda subsystem:
                                     subsystem.get('change_count', 0), summary.values()))
            last_changes = list(map(lambda subsystem:
                                    subsystem.get('last_change', start_time), summary.values()))
            last_updates = list(map(lambda subsystem:
                                    subsystem.get('last_update', start_time), summary.values()))
            state_summary.update({
                'state_summary_change_count': sum(change_counts),
                'state_summary_last_change': max(last_changes),
                'state_summary_last_update': max(last_updates)
            })
            summary, detail = self._get_combined_summary(summary)
            state_summary['state_summary'] = summary
            state_summary['state_summary_detail'] = detail
        except Exception as e:
            state_summary.update({
                'state_summary': 'error',
                'state_summary_detail': str(e)
            })
        return state_summary

    def _get_combined_summary(self, summary):
        has_error = False
        has_warning = False
        for subsystem_name in summary:
            subsystem = summary[subsystem_name]
            state = subsystem.get('state', 'error')
            detail = subsystem.get('detail', 'unknown')
            if state == 'broken':
                has_error = True
                error_detail = self._DETAIL_FORMAT % (subsystem_name, state, detail)
            elif state != 'healthy':
                has_warning = True
                warning_detail = self._DETAIL_FORMAT % (subsystem_name, state, detail)
        if has_error:
            return 'broken', error_detail
        elif has_warning:
            return 'damaged', warning_detail
        return 'healthy', None

    def _get_state_summary(self):
        return {
            'cpn': self._cpn_collector.get_cpn_summary(),
            'process': self._local_collector.get_process_summary(),
            'dataplane': self._faucet_collector.get_dataplane_summary(),
            'switch': self._faucet_collector.get_switch_summary()
        }

    def get_switch_state(self, path, params):
        """Get the state of the switches"""
        return self._faucet_collector.get_switch_state()

    def get_dataplane_state(self, path, params):
        """Get the dataplane state overview"""
        return self._faucet_collector.get_dataplane_state()

    def get_host_path(self, path, params):
        """Get active host path"""
        src = params.get('src', None)
        dst = params.get('dst', None)
        return self._faucet_collector.get_host_path(src, dst)

    def get_cpn_state(self, path, params):
        """Get CPN state"""
        return self._cpn_collector.get_cpn_state()

    def get_process_state(self, path, params):
        """Get certain processes state on the controller machine"""
        return self._local_collector.get_process_state()


def load_config():
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
    HTTP = forch.http_server.HttpServer(CONFIG.get('http', {}))
    HTTP.map_request('system_state', FORCH.get_system_state)
    HTTP.map_request('dataplane_state', FORCH.get_dataplane_state)
    HTTP.map_request('switch_state', FORCH.get_switch_state)
    HTTP.map_request('cpn_state', FORCH.get_cpn_state)
    HTTP.map_request('process_state', FORCH.get_process_state)
    HTTP.map_request('host_path', FORCH.get_host_path)
    HTTP.map_request('', HTTP.static_file(''))
    HTTP.start_server()
    FORCH.main_loop()
    LOGGER.warning('Exiting program')
    HTTP.stop_server()
