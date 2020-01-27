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
from forch.proto.device_pb2 import Device

LOGGER = logging.getLogger('faucetizer')


class Faucetizer:
    """Collect Faucet information and generate ACLs"""
    def __init__(self, output_file):
        self._devices = {}
        self._base_faucet_config = None
        self._output_file = output_file

    def process_network_state(self, network_state):
        """Process network state input"""
        for mac, learning in network_state.device_mac_learnings.items():
            self._process_device_learning(mac, learning)
        for mac, behavior in network_state.device_mac_behaviors.items():
            self._process_device_behavior(mac, behavior)

        self._faucetize()

    def _process_device_learning(self, mac, learning):
        if learning.connecting:
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

    def _faucetize(self):
        if not self._base_faucet_config:
            raise Exception("Base faucet configuration not provided")

        out_faucet_config = copy.deepcopy(self._base_faucet_config)
        for mac, device in self._devices.items():
            if device.learning and device.behavior:
                switch = device.learning.switch
                port = device.learning.port
                switch_config = out_faucet_config.get('dps', {}).get(switch, {})
                port_config = switch_config.get('interfaces', {}).get(port)

                if not port_config:
                    LOGGER.warning('Switch or port not defined in faucet config: %s %s',
                                   switch, port)
                    continue

                port_config['native_vlan'] = device.behavior.vid
                role = device.behavior.role
                if role:
                    port_config['acls_in'] = [f'role_{role}']

        self._generate_faucet_config(out_faucet_config)

    def _generate_faucet_config(self, out_faucet_config):
        try:
            with open(self._output_file, 'w') as config_output:
                yaml.dump(out_faucet_config, config_output)

        except IOError as error:
            LOGGER.error('Cannot write faucet config: %s', error)
        except Exception as error:
            LOGGER.error('Cannot commit config: %s', error)

        LOGGER.info('Config wrote to %s', self._output_file)


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
    print(sys.argv)
    ARGS = parse_args(sys.argv[1:])

    OUTPUT_FILE = os.path.join(FAUCET_BASE_DIR, ARGS.output)
    FAUCETIZER = Faucetizer(OUTPUT_FILE)

    FAUCET_CONFIG_FILE = os.path.join(FORCH_BASE_DIR, ARGS.config_input)
    FAUCET_CONFIG = load_faucet_config(FAUCET_CONFIG_FILE)
    FAUCETIZER.process_faucet_config(FAUCET_CONFIG)

    NETWORK_STATE_FILE = os.path.join(FORCH_BASE_DIR, ARGS.state_input)
    NETWORK_STATE_SAMPLES = load_network_state(NETWORK_STATE_FILE)
    FAUCETIZER.process_network_state(NETWORK_STATE_SAMPLES)
