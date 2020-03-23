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
from forch.proto.forch_configuration_pb2 import OrchestrationConfig

LOGGER = logging.getLogger('faucetizer')


class Faucetizer:
    """Collect Faucet information and generate ACLs"""
    def __init__(self, orch_config, structural_config_file, segments_to_vlans,
                 behavioral_config_file):
        self._dynamic_devices = {}
        self._static_devices = {}
        self._segments_to_vlans = segments_to_vlans
        self._structural_faucet_config = None
        self._behavioral_faucet_config = None
        self._config = orch_config
        self._structural_config_file = structural_config_file
        self._behavioral_config_file = behavioral_config_file
        self._lock = threading.Lock()
        self.reload_structural_config()

    def process_device_placement(self, eth_src, placement, static=False):
        """Process device placement"""
        devices = self._static_devices if static else self._dynamic_devices
        device_type = "static" if static else "dynamic"
        with self._lock:
            if placement.connected:
                device = devices.setdefault(eth_src, Device())
                device.placement.CopyFrom(placement)
                LOGGER.info(
                    'Added %s placement: %s, %s, %s',
                    device_type, eth_src, placement.switch, placement.port)
            else:
                removed = devices.pop(eth_src, None)
                if removed:
                    LOGGER.info('Removed %s device: %s', device_type, eth_src)

            self.flush_behavioral_config()

    def process_device_behavior(self, eth_src, behavior, static=False):
        """Process device behavior"""
        devices = self._static_devices if static else self._dynamic_devices
        device_type = "static" if static else "dynamic"
        with self._lock:
            if behavior.segment:
                device = devices.setdefault(eth_src, Device())
                device.behavior.CopyFrom(behavior)
                LOGGER.info(
                    'Added %s behavior: %s, %s, %s',
                    device_type, eth_src, behavior.segment, behavior.role)
            else:
                device = devices.get(eth_src)
                if device:
                    device.behavior.Clear()
                    LOGGER.info('Removed %s behavior: %s', device_type, eth_src)

            self.flush_behavioral_config()

    def process_faucet_config(self, faucet_config):
        """Process faucet config when structural faucet config changes"""
        with self._lock:
            self._structural_faucet_config = copy.copy(faucet_config)

            self.flush_behavioral_config()

    def _faucetize(self):
        if not self._structural_faucet_config:
            raise Exception("Structural faucet configuration not provided")

        behavioral_faucet_config = copy.deepcopy(self._structural_faucet_config)
        devices = {**self._dynamic_devices, **self._static_devices}
        for mac, device in devices.items():
            if device.placement.switch and device.behavior.segment:
                switch_cfg = behavioral_faucet_config.get('dps', {}).get(
                    device.placement.switch, {})
                port_cfg = switch_cfg.get('interfaces', {}).get(device.placement.port)

                if not port_cfg:
                    LOGGER.warning('Switch or port not defined in faucet config: %s, %s',
                                   device.placement.switch, device.placement.port)
                    continue

                vid = self._segments_to_vlans.get(device.behavior.segment)
                if not vid:
                    LOGGER.warning('Device segment does not have a matching vlan: %s, %s',
                                   mac, device.behavior.segment)
                    continue

                port_cfg['native_vlan'] = vid
                if device.behavior.role:
                    port_cfg['acls_in'] = [f'role_{device.behavior.role}']

        self._behavioral_faucet_config = behavioral_faucet_config

    def reload_structural_config(self):
        """Reload structural config from file"""
        with open(self._structural_config_file) as structural_config_file:
            structural_config = yaml.safe_load(structural_config_file)
            self.process_faucet_config(structural_config)

    def flush_behavioral_config(self, force=False):
        """Generate and write behavioral config to file"""
        if not force and self._config.faucetize_interval_sec:
            return
        self._faucetize()
        with open(self._behavioral_config_file, 'w') as file:
            yaml.dump(self._behavioral_faucet_config, file)


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


def parse_args(raw_args):
    """Parse sys args"""
    parser = argparse.ArgumentParser(prog='faucetizer', description='faucetizer')
    parser.add_argument('-s', '--state-input', type=str, default='devices_state.yaml',
                        help='devices state input')
    parser.add_argument('-g', '--segments-vlans', type=str, default='segments-to-vlans.yaml',
                        help='segments to vlans mapping input file')
    parser.add_argument('-c', '--config-input', type=str, default='faucet.yaml',
                        help='structural faucet config input')
    parser.add_argument('-o', '--output', type=str, default='faucet.yaml',
                        help='behavioral faucet config output')
    return parser.parse_args(raw_args)


if __name__ == '__main__':
    configure_logging()
    FORCH_BASE_DIR = os.getenv('FORCH_CONFIG_DIR')
    FAUCET_BASE_DIR = os.getenv('FAUCET_CONFIG_DIR')
    ARGS = parse_args(sys.argv[1:])

    SEGMENTS_VLANS_FILE = os.path.join(FORCH_BASE_DIR, ARGS.segments_vlans)
    SEGMENTS_TO_VLANS = load_segments_to_vlans(SEGMENTS_VLANS_FILE)
    LOGGER.info('Loaded %d mappings', len(SEGMENTS_TO_VLANS.segments_to_vlans))

    ORCH_CONFIG = OrchestrationConfig()
    STRUCTURAL_CONFIG_FILE = os.path.join(FORCH_BASE_DIR, ARGS.config_input)
    BEHAVIORAL_CONFIG_FILE = os.path.join(FAUCET_BASE_DIR, ARGS.output)

    FAUCETIZER = Faucetizer(
        ORCH_CONFIG, STRUCTURAL_CONFIG_FILE, SEGMENTS_TO_VLANS.segments_to_vlans,
        BEHAVIORAL_CONFIG_FILE)

    DEVICES_STATE_FILE = os.path.join(FORCH_BASE_DIR, ARGS.state_input)
    DEVICES_STATE = load_devices_state(DEVICES_STATE_FILE)
    process_devices_state(FAUCETIZER, DEVICES_STATE)

    LOGGER.info('Processed device state and config wrote to %s', BEHAVIORAL_CONFIG_FILE)
