"""Collect Faucet information and generate ACLs"""

import argparse
import copy
import logging
import os
import sys
import yaml

from forch.forchestrator import configure_logging
from forch.utils import yaml_proto

from forch.proto.network_state_pb2 import NetworkState
from forch.proto.network_state_pb2 import Device

LOGGER = logging.getLogger('faucetizer')


class Faucetizer:
    """Collect Faucet information and generate ACLs"""
    def __init__(self):
        self._devices = {}
        self._base_faucet_config = None
        self._dynamic_faucet_config = None
        self.faucetizer = None
        self.authenticator = None

    def process_network_state(self, network_state):
        """Process network state input"""
        for mac, learning in network_state.device_mac_learnings.items():
            self._process_device_learning(mac, learning)
        for mac, behavior in network_state.device_mac_behaviors.items():
            self._process_device_behavior(mac, behavior)

        self._faucetize()

    def _process_device_learning(self, mac, learning):
        if learning.connected:
            device = self._devices.setdefault(mac, Device())
            device.learning.CopyFrom(learning)
        else:
            self._devices.pop(mac, None)

    def _process_device_behavior(self, mac, behavior):
        device = self._devices.setdefault(mac, Device())
        device.behavior.CopyFrom(behavior)

    def process_faucet_config(self, faucet_config):
        """Process faucet config when base faucet config changes"""
        self._base_faucet_config = faucet_config
        self._faucetize()

    def process_device_placement(self, device_placement):
        if self.faucetizer:
            self.faucetizer.process_device_placement(device_placement)
        if self.authenticator:
            self.authenticator.process_device_placement(device_placement)

    def _faucetize(self):
        if not self._base_faucet_config:
            raise Exception("Base faucet configuration not provided")

        dynamic_faucet_config = copy.deepcopy(self._base_faucet_config)
        for mac, device in self._devices.items():
            if device.learning and device.behavior:
                switch = device.learning.switch
                port = device.learning.port
                switch_config = dynamic_faucet_config.get('dps', {}).get(switch, {})
                port_config = switch_config.get('interfaces', {}).get(port)

                if not port_config:
                    LOGGER.warning('Switch or port not defined in faucet config: %s %s',
                                   switch, port)
                    continue

                port_config['native_vlan'] = device.behavior.vid
                role = device.behavior.role
                if role:
                    port_config['acls_in'] = [f'role_{role}']

        self._dynamic_faucet_config = dynamic_faucet_config

    def get_dynamic_faucet_config(self):
        """Return dynamic faucet config"""
        return self._dynamic_faucet_config


def load_network_state(file):
    """Load network state file"""
    LOGGER.info('Loading network state file %s', file)
    network_state = yaml_proto(file, NetworkState)
    LOGGER.info('Loaded %d devices', len(network_state.device_mac_behaviors))
    return network_state


def load_faucet_config(file):
    """Load network state file"""
    LOGGER.info('Loading faucet config file %s', file)
    with open(file) as config_file:
        faucet_config = yaml.safe_load(config_file)
    LOGGER.info('Loaded base faucet config')
    return faucet_config


def write_faucet_config(faucet_config, out_path):
    """Write faucet config to file"""
    try:
        with open(out_path, 'w') as out_file:
            yaml.dump(faucet_config, out_file)
        LOGGER.info('Config wrote to %s', out_path)
    except Exception as error:
        LOGGER.error('Cannot write faucet config: %s', error)


def parse_args(raw_args):
    """Parse sys args"""
    parser = argparse.ArgumentParser(prog='faucetizer', description='faucetizer')
    parser.add_argument('-s', '--state-input', type=str, default='network_state.yaml',
                        help='network state input')
    parser.add_argument('-c', '--config-input', type=str, default='faucet.yaml',
                        help='faucet base config input')
    parser.add_argument('-o', '--output', type=str, default='faucet.yaml',
                        help='faucet orchestration config output')
    return parser.parse_args(raw_args)


if __name__ == '__main__':
    configure_logging()
    FORCH_BASE_DIR = os.getenv('FORCH_CONFIG_DIR')
    FAUCET_BASE_DIR = os.getenv('FAUCET_CONFIG_DIR')
    ARGS = parse_args(sys.argv[1:])

    FAUCETIZER = Faucetizer()

    FAUCET_CONFIG_FILE = os.path.join(FORCH_BASE_DIR, ARGS.config_input)
    FAUCET_CONFIG = load_faucet_config(FAUCET_CONFIG_FILE)
    FAUCETIZER.process_faucet_config(FAUCET_CONFIG)

    NETWORK_STATE_FILE = os.path.join(FORCH_BASE_DIR, ARGS.state_input)
    NETWORK_STATE_SAMPLES = load_network_state(NETWORK_STATE_FILE)
    FAUCETIZER.process_network_state(NETWORK_STATE_SAMPLES)

    OUTPUT_FILE = os.path.join(FAUCET_BASE_DIR, ARGS.output)
    write_faucet_config(FAUCETIZER.get_dynamic_faucet_config(), OUTPUT_FILE)
