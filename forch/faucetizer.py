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

from forch.proto.devices_state_pb2 import DevicesState, Device, SegmentsToVlans

LOGGER = logging.getLogger('faucetizer')


class Faucetizer:
    """Collect Faucet information and generate ACLs"""
    def __init__(self, structural_faucet_config, segments_to_vlans):
        self._devices = {}
        self._segments_to_vlans = segments_to_vlans
        self._structural_faucet_config = structural_faucet_config
        self._behavioral_faucet_config = None
        self._lock = threading.Lock()
        print(self._structural_faucet_config)
        print(self._segments_to_vlans)

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

    def process_segments_to_vlans(self, segments_to_vlans):
        """Process single segment vlan mapping"""
        self._segments_to_vlans.update(segments_to_vlans.segments_to_vlans)

    def process_faucet_config(self, faucet_config):
        """Process faucet config when structural faucet config changes"""
        with self._lock:
            self._structural_faucet_config = copy.copy(faucet_config)

    def _faucetize(self):
        if not self._structural_faucet_config:
            raise Exception("Structural faucet configuration not provided")

        behavioral_faucet_config = copy.deepcopy(self._structural_faucet_config)
        for mac, device in self._devices.items():
            if device.placement.switch and device.behavior.vid:
                switch_cfg = behavioral_faucet_config.get('dps', {}).get(
                    device.placement.switch, {})
                port_cfg = switch_cfg.get('interfaces', {}).get(device.placement.port)

                if not port_cfg:
                    LOGGER.warning('Switch or port not defined in faucet config: %s, %s',
                                   device.placement.switch, device.placement.port)
                    continue

                vid = self._segments_to_vlans.get(device.behavior.segment)
                if not vid:
                    raise Exception('Device segment does not have a matching vlan %s %s',
                                    mac, device.behavior.segment)
                port_cfg['native_vlan'] = vid
                if device.behavior.role:
                    port_cfg['acls_in'] = [f'role_{device.behavior.role}']

        self._behavioral_faucet_config = behavioral_faucet_config

    def get_behavioral_faucet_config(self):
        """Return behavioral faucet config"""
        with self._lock:
            self._faucetize()
            return self._behavioral_faucet_config


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


def load_segments_to_vlans(file):
    """Load segments to vlans mapping from file"""
    segments_to_vlans = yaml_proto(file, SegmentsToVlans)
    return segments_to_vlans


def load_faucet_config(file):
    """Load network state file"""
    with open(file) as config_file:
        return yaml.safe_load(config_file)


def update_structural_config(faucetizer: Faucetizer, file):
    """Read structural config from file and update in faucetizer"""
    with open(file) as structural_config_file:
        structural_config = yaml.safe_load(structural_config_file)
        faucetizer.process_faucet_config(structural_config)


def write_behavioral_config(faucetizer: Faucetizer, file):
    """Get behavioral config from faucetizer and write to file"""
    behavioral_config = faucetizer.get_behavioral_faucet_config()
    with open(file, 'w') as behavioral_config_file:
        yaml.dump(behavioral_config, behavioral_config_file)


def parse_args(raw_args):
    """Parse sys args"""
    parser = argparse.ArgumentParser(prog='faucetizer', description='faucetizer')
    parser.add_argument('-s', '--state-input', type=str, default='devices_state.yaml',
                        help='devices state input')
    parser.add_argument('-g', '--segments-vlans', type=str, default='segments-to-vlans.yaml',
                        help='segments to vlans mapping input file')
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

    SEGMENTS_VLANS_FILE = os.path.join(FORCH_BASE_DIR, ARGS.segments_vlans)
    SEGMENTS_TO_VLANS = load_segments_to_vlans(SEGMENTS_VLANS_FILE)
    LOGGER.info('Loaded %d mappings', len(SEGMENTS_TO_VLANS.segments_to_vlans))

    FAUCETIZER = Faucetizer(STRUCTURAL_CONFIG, SEGMENTS_TO_VLANS.segments_to_vlans)

    DEVICES_STATE_FILE = os.path.join(FORCH_BASE_DIR, ARGS.state_input)
    DEVICES_STATE = load_devices_state(DEVICES_STATE_FILE)
    process_devices_state(FAUCETIZER, DEVICES_STATE)

    OUTPUT_FILE = os.path.join(FAUCET_BASE_DIR, ARGS.output)
    write_behavioral_config(FAUCETIZER, OUTPUT_FILE)
    LOGGER.info('Config wrote to %s', OUTPUT_FILE)
