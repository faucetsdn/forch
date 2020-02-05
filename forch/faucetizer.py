"""Collect Faucet information and generate ACLs"""

import argparse
import copy
import logging
import os
import sys
import threading
import yaml

from forch.utils import configure_logging
from forch.utils import yaml_proto

from forch.proto.network_state_pb2 import DevicesState
from forch.proto.network_state_pb2 import Device
from forch.proto.network_state_pb2 import DevicePlacement
from forch.proto.network_state_pb2 import DeviceBehavior

LOGGER = logging.getLogger('faucetizer')


class Faucetizer:
    """Collect Faucet information and generate ACLs"""
    def __init__(self, structural_faucet_config):
        self._devices = {}
        self._structural_faucet_config = structural_faucet_config
        self._dynamic_faucet_config = None
        self._lock = threading.Lock()

    def process_device_placement(self, eth_src, placement):
        """Process device placement"""
        with self._lock:
            if placement.connected:
                device = self._devices.setdefault(eth_src, Device())
                device.placement.CopyFrom(placement)
            else:
                self._devices.pop(placement.eth_src, None)

    def process_device_behavior(self, eth_src, behavior):
        """Process device placement"""
        with self._lock:
            device = self._devices.setdefault(eth_src, Device())
            device.behavior.CopyFrom(behavior)

    def process_faucet_config(self, faucet_config):
        """Process faucet config when structural faucet config changes"""
        with self._lock:
            self._structural_faucet_config = copy.copy(faucet_config)
            self._faucetize()

    def _faucetize(self):
        if not self._structural_faucet_config:
            raise Exception("Structural faucet configuration not provided")

        dynamic_faucet_config = copy.deepcopy(self._structural_faucet_config)
        for mac, device in self._devices.items():
            if device.placement and device.behavior:
                switch_cfg = dynamic_faucet_config.get('dps', {}).get(device.placement.switch, {})
                port_cfg = switch_cfg.get('interfaces', {}).get(device.placement.port)

                if not port_cfg:
                    LOGGER.warning('Switch or port not defined in faucet config: %s %s',
                                   device.switch, device.port)
                    continue

                port_cfg['native_vlan'] = device.vid
                if device.role:
                    port_cfg['acls_in'] = [f'role_{device.role}']

        self._dynamic_faucet_config = dynamic_faucet_config

    def get_dynamic_faucet_config(self):
        """Return dynamic faucet config"""
        with self._lock:
            return self._dynamic_faucet_config


def load_network_state(file):
    """Load network state file"""
    LOGGER.info('Loading network state file %s', file)
    network_state = yaml_proto(file, DevicesState)
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
