"""Collect Faucet information and generate ACLs"""

import json
import logging
import os
from queue import SimpleQueue
import sys
import threading
import yaml

from faucet import config_parser

from forch.forchestrator import configure_logging
from forch.utils import proto_dict
from forch.utils import yaml_proto

from forch.proto.network_state_pb2 import NetworkState, DeviceLearning, DeviceBehavior

LOGGER = logging.getLogger('faucetizer')


class Faucetizer:
    """Collect Faucet information and generate ACLs"""
    def __init__(self, output_file):
        self._devices = {}
        self._base_faucet_config = None
        self._faucet_config = None
        self._queue = SimpleQueue()
        self._worker_thread = threading.Thread(target=self._main_loop)
        self._output_file = output_file

    def _process_network_state(self, network_state):
        macs = set()
        for mac, learning in network_state.device_mac_learnings.items():
            macs.add(mac)
            self._process_device_learning(mac, learning)
        for mac, behavior in network_state.device_mac_behaviors.items():
            macs.add(mac)
            self._process_device_behavior(mac, behavior)

        self._faucetize(macs)

    def _process_device_learning(self, mac, learning):
        device_map = self._devices.setdefault(mac, {})
        device_map['new_switch'] = learning.switch
        device_map['new_port'] = learning.port

    def _process_device_behavior(self, mac, behavior):
        device_map = self._devices.setdefault(mac, {})
        device_map['vlan'] = behavior.vid
        device_map['role'] = behavior.role

    def _process_faucet_config(self, faucet_config):
        """Process faucet config when base faucet config changes"""
        self._base_faucet_config = faucet_config
        self._faucet_config = faucet_config
        self._faucetize()

    def _faucetize(self, macs=None):
        if not self._faucet_config:
            return

        if not macs:
            macs = self._devices.keys()

        commit = False

        for mac in macs:
            old_switch = self._devices.get(mac, {}).get('old_switch')
            old_port = self._devices.get(mac, {}).get('old_port')
            new_switch = self._devices.get(mac, {}).get('new_switch')
            new_port = self._devices.get(mac, {}).get('new_port')

            if old_switch != new_switch or old_port != new_port:
                self._reset_port_config(old_switch, old_port)
                commit = True

            vlan = self._devices.get(mac, {}).get('vlan')
            role = self._devices.get(mac, {}).get('role')

            if new_switch and vlan and role:
                switch_config = self._faucet_config.get('dps', {}).get(new_switch, {})
                port_config = switch_config.get('interfaces', {}).get(new_port)
                if not port_config:
                    LOGGER.warning('Switch or port not defined in faucet config: %s %s',
                                 new_switch, new_port)
                    continue
                port_config['native_vlan'] = vlan
                port_config['acls_in'] = [f'role_{role}']
                commit = True

        if commit:
            self._commit_faucet_config(macs)

    def _reset_port_config(self, switch, port):
        if not switch or not port:
            return

        switch_config = self._faucet_config.get('dps', {}).get('switch', {})
        port_config = switch_config.get('interfaces', {}).get(port)
        if not port_config:
            LOGGER.warning('Switch or port not defined in faucet config: %s %s', switch, port)
            return

        base_switch_config = self._base_faucet_config.get('dps', {}).get('switch', {})
        base_port_config = base_switch_config.get('interfaces', {}).get(port)
        if not base_port_config:
            LOGGER.warning('Switch or port not defined in base faucet config: %s %s', switch, port)
            return

        port_config.update(base_port_config)

    def _commit_faucet_config(self, macs):
        for mac in macs:
            device_map = self._devices[mac]
            device_map['old_switch'] = device_map['new_switch']
            device_map['old_port'] = device_map['new_port']

        with open(self._output_file, 'w') as config_output:
            yaml.dump(self._faucet_config, config_output)

        LOGGER.info('Config wrote to %s', self._output_file)

    def _main_loop(self):
        while True:
            message = self._queue.get()
            if isinstance(message, NetworkState):
                self._process_network_state(message)
            elif 'dps' in message: # TODO: need a faucet config proto
                self._process_faucet_config(message)
            else:
                LOGGER.warning('Received unknown type message: %s', type(message))

    def enqueue(self, message):
        self._queue.put(message, block=True)

    def start(self):
        self._worker_thread.start()


def load_network_state(base_dir_name):
    """Load network state file"""
    file = os.path.join(base_dir_name, 'network_state.yaml')
    LOGGER.info('Loading network state file %s', file)
    network_state = yaml_proto(file, NetworkState)
    LOGGER.info('Loaded %d devices', len(network_state.device_mac_behaviors))
    return network_state


def load_faucet_config(base_dir_name):
    """Load network state file"""
    file = os.path.join(base_dir_name, 'faucet_base.yaml')
    LOGGER.info('Loading faucet config file %s', file)
    with open(file) as config_file:
          faucet_config = yaml.safe_load(config_file)
    LOGGER.info('Loaded base faucet config')
    return faucet_config


if __name__ == '__main__':
    configure_logging()
    FORCH_BASE_DIR = os.getenv('FORCH_CONFIG_DIR')
    FAUCET_BASE_DIR = os.getenv('FAUCET_CONFIG_DIR')

    OUTPUT = os.path.join(FAUCET_BASE_DIR, 'faucet.yaml')
    FAUCETIZER = Faucetizer(OUTPUT)
    FAUCETIZER.start()

    NETWORK_STATE_SAMPLES = load_network_state(FORCH_BASE_DIR)
    FAUCETIZER.enqueue(NETWORK_STATE_SAMPLES)

    FAUCET_CONFIG = load_faucet_config(FORCH_BASE_DIR)
    FAUCETIZER.enqueue(FAUCET_CONFIG)
