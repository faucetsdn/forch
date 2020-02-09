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

from forch.proto.devices_state_pb2 import DevicesState
from forch.proto.devices_state_pb2 import Device

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

    def _faucetize(self):
        if not self._structural_faucet_config:
            raise Exception("Structural faucet configuration not provided")

        dynamic_faucet_config = copy.deepcopy(self._structural_faucet_config)
        for mac, device in self._devices.items():
            if device.placement.switch and device.behavior.vid:
                switch_cfg = dynamic_faucet_config.get('dps', {}).get(device.placement.switch, {})
                port_cfg = switch_cfg.get('interfaces', {}).get(device.placement.port)

                if not port_cfg:
                    LOGGER.warning('Switch or port not defined in faucet config: %s, %s',
                                   device.placement.switch, device.placement.port)
                    continue

                port_cfg['native_vlan'] = device.behavior.vid
                if device.behavior.role:
                    port_cfg['acls_in'] = [f'role_{device.behavior.role}']

        self._dynamic_faucet_config = dynamic_faucet_config

    def get_dynamic_faucet_config(self):
        """Return dynamic faucet config"""
        with self._lock:
            self._faucetize()
            return self._dynamic_faucet_config


def load_devices_state(file):
    """Load devices state file"""
    LOGGER.info('Loading network state file %s', file)
    devices_state = yaml_proto(file, DevicesState)
    LOGGER.info('Loaded %d devices', len(devices_state.device_mac_behaviors))
    return devices_state


def process_devices_state(faucetizer: Faucetizer, devices_state: DevicesState):
    """Process devices state"""
    for mac, device_placement in devices_state.device_mac_placements.items():
        faucetizer.process_device_placement(mac, device_placement)
    for mac, device_behavor in devices_state.device_mac_behaviors.items():
        faucetizer.process_device_behavior(mac, device_behavor)


def load_faucet_config(file):
    """Load network state file"""
    with open(file) as config_file:
        return yaml.safe_load(config_file)


def update_structural_config(faucetizer: Faucetizer, file):
    """Read structural config from file and update in faucetizer"""
    with open(file) as structural_config_file:
        structural_config = yaml.safe_load(structural_config_file)
        faucetizer.process_faucet_config(structural_config)


def write_dynamic_config(faucetizer: Faucetizer, file):
    """Get dynamic config from faucetizer and write to file"""
    dynamic_config = faucetizer.get_dynamic_faucet_config()
    with open(file, 'w') as dynamic_config_file:
        yaml.dump(dynamic_config, dynamic_config_file)


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

    STRUCTURAL_CONFIG_FILE = os.path.join(FORCH_BASE_DIR, ARGS.config_input)
    STRUCTURAL_CONFIG = load_faucet_config(STRUCTURAL_CONFIG_FILE)
    LOGGER.info('Loaded structural faucet config from %s', STRUCTURAL_CONFIG_FILE)

    FAUCETIZER = Faucetizer(STRUCTURAL_CONFIG)

    DEVICES_STATE_FILE = os.path.join(FORCH_BASE_DIR, ARGS.state_input)
    DEVICES_STATE = load_devices_state(DEVICES_STATE_FILE)
    process_devices_state(FAUCETIZER, DEVICES_STATE)

    OUTPUT_FILE = os.path.join(FAUCET_BASE_DIR, ARGS.output)
    write_dynamic_config(FAUCETIZER, OUTPUT_FILE)
    LOGGER.info('Config wrote to %s', OUTPUT_FILE)
