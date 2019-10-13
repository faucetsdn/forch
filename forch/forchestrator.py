"""Orchestrator component for controlling a Faucet SDN"""

import logging
import os
import sys
import yaml

import configurator
import faucet_event_client
import http_server

from cpn_state_collector import CPNStateCollector
from faucet_state_collector import FaucetStateCollector
from local_state_collector import LocalStateCollector

LOGGER = logging.getLogger('forch')


class Forchestrator:
    """Main class encompassing faucet orchestrator components for dynamically
    controlling faucet ACLs at runtime"""

    _FCONFIG_DEFAULT = 'forch.yaml'

    def __init__(self, dconfig):
        self._dconfig = dconfig
        self._faucet_events = None
        self._oconfig = None
        self._server = None
        self._faucet_collector = FaucetStateCollector()
        self._local_collector = LocalStateCollector()
        self._cpn_collector = CPNStateCollector()

    def initialize(self):
        """Initialize forchestrator instance"""
        config_root = os.getenv('FORCH_CONFIG_DIR', '.')
        config_file = self._dconfig.get('forch_config', self._FCONFIG_DEFAULT)
        config_path = os.path.join(config_root, config_file)
        LOGGER.info('Reading config file %s', os.path.abspath(config_path))
        with open(config_path, 'r') as stream:
            self._oconfig = yaml.safe_load(stream)
        LOGGER.info('Attaching event channel...')
        self._faucet_events = faucet_event_client.FaucetEventClient(self._dconfig)
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
        overview = {
            'peer_controller_url': self._get_peer_controller_url(),
            'processes': self._local_collector.get_process_overview(),
            'dataplane': self._faucet_collector.get_dataplane_state(),
            'site_name': self._oconfig['site']['name']
        }
        overview.update(self._faucet_collector.get_controller_state())
        return overview

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


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    CONFIG = configurator.Configurator().parse_args(sys.argv)
    FORCH = Forchestrator(CONFIG)
    FORCH.initialize()
    HTTP = http_server.HttpServer(CONFIG)
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
