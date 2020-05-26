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

from forch.proto.devices_state_pb2 import DevicesState, SegmentsToVlans
from forch.proto.devices_state_pb2 import DevicePlacement, DeviceBehavior
from forch.proto.forch_configuration_pb2 import ForchConfig
from forch.proto.shared_constants_pb2 import DVAState

LOGGER = logging.getLogger('faucetizer')

ACL_FILE_SUFFIX = '_augmented'


class Faucetizer:
    """Collect Faucet information and generate ACLs"""
    # pylint: disable=too-many-arguments
    def __init__(self, orch_config, structural_config_file, segments_to_vlans,
                 behavioral_config_file, reregister_acl_file_handlers=None):
        self._static_devices = DevicesState()
        self._dynamic_devices = DevicesState()
        self._vlan_states = {}
        self._segments_to_vlans = segments_to_vlans
        self._structural_faucet_config = None
        self._behavioral_faucet_config = None
        self._behavioral_include = None
        self._next_cookie = None
        self._config = orch_config
        self._structural_config_file = structural_config_file
        self._behavioral_config_file = behavioral_config_file
        self._watched_acl_files = []
        self._reregister_acl_file_handlers = reregister_acl_file_handlers
        self._lock = threading.RLock()

    def process_device_placement(self, eth_src, placement, static=False):
        """Process device placement"""
        if not placement.switch or not placement.port:
            raise Exception(f'Incomplete placement for {eth_src}: {placement}')
        devices_state = self._static_devices if static else self._dynamic_devices
        device_type = "static" if static else "dynamic"
        with self._lock:
            device_placements = devices_state.device_mac_placements
            if placement.connected:
                device_placement = device_placements.setdefault(eth_src, DevicePlacement())
                device_placement.CopyFrom(placement)
                LOGGER.info(
                    'Received %s placement: %s, %s, %s',
                    device_type, eth_src, device_placement.switch, device_placement.port)
            else:
                removed = device_placements.pop(eth_src, None)
                if removed:
                    LOGGER.info('Removed %s placement: %s', device_type, eth_src)

            self.flush_behavioral_config()

    def process_device_behavior(self, eth_src, behavior, static=False):
        """Process device behavior"""
        devices_state = self._static_devices if static else self._dynamic_devices
        device_type = "static" if static else "dynamic"
        with self._lock:
            device_behaviors = devices_state.device_mac_behaviors
            if behavior.segment:
                device_behavior = device_behaviors.setdefault(eth_src, DeviceBehavior())
                device_behavior.CopyFrom(behavior)
                LOGGER.info(
                    'Received %s behavior: %s, %s, %s',
                    device_type, eth_src, device_behavior.segment, device_behavior.role)
            else:
                removed = device_behaviors.pop(eth_src, None)
                if removed:
                    LOGGER.info('Removed %s behavior: %s', device_type, eth_src)

            self.flush_behavioral_config()

    def _process_structural_config(self, faucet_config):
        """Process faucet config when structural faucet config changes"""
        with self._lock:
            self._structural_faucet_config = copy.copy(faucet_config)

            self._next_cookie = 1
            behavioral_include = []
            new_watched_acl_files = []
            config_dir = os.path.dirname(self._structural_config_file)
            for acl_file_name in self._structural_faucet_config.get('include', []):
                acl_file_path = os.path.join(config_dir, acl_file_name)
                self.reload_acl_file(acl_file_path)
                behavioral_include.append(self._augment_acl_file_path(acl_file_name))
                new_watched_acl_files.append(acl_file_path)

            self._behavioral_include = behavioral_include

            if not self._config.faucetize_interval_sec and self._reregister_acl_file_handlers:
                self._reregister_acl_file_handlers(self._watched_acl_files, new_watched_acl_files)
            self._watched_acl_files = new_watched_acl_files

            self.flush_behavioral_config()

    def _process_acl_config(self, file_path, acls_config):
        new_acls_config = copy.copy(acls_config)

        if not self._next_cookie:
            raise Exception('Cookie is not initialized')

        with self._lock:
            for rule_list in acls_config.get('acls', {}).values():
                for rule_map in rule_list:
                    if 'rule' in rule_map:
                        rule_map['rule']['cookie'] = self._next_cookie
                        self._next_cookie += 1

        new_file_path = self._augment_acl_file_path(file_path)
        self.flush_acl_config(new_file_path, new_acls_config)

    def _augment_acl_file_path(self, file_path):
        base_file_path, ext = os.path.splitext(file_path)
        return base_file_path + ACL_FILE_SUFFIX + ext

    def _is_access_port(self, port_cfg):
        non_access_port_properties = ['stack', 'lacp', 'output_only', 'tagged_vlans']
        port_properties = [
            property for property in non_access_port_properties if property in port_cfg]
        return len(port_properties) == 0

    def _update_vlan_state(self, switch, port, state):
        self._vlan_states.setdefault(switch, {})[port] = state

    def _initialize_host_ports(self):
        if not self._structural_faucet_config:
            raise Exception('Structural faucet configuration not provided')

        behavioral_faucet_config = copy.deepcopy(self._structural_faucet_config)

        for switch, switch_map in behavioral_faucet_config.get('dps', {}).items():
            for port, port_map in switch_map.get('interfaces', {}).items():
                if not self._is_access_port(port_map):
                    continue
                if self._config.unauthenticated_vlan:
                    port_map['native_vlan'] = self._config.unauthenticated_vlan
                    self._update_vlan_state(switch, port, DVAState.unauthenticated)
                if self._config.tail_acl:
                    port_map['acls_in'] = [self._config.tail_acl]

        return behavioral_faucet_config

    # pylint: disable=too-many-branches
    def _faucetize(self):

        behavioral_faucet_config = self._initialize_host_ports()

        # static information of a device should overwrite the corresponding dynamic one
        device_placements = {**self._dynamic_devices.device_mac_placements,
                             **self._static_devices.device_mac_placements}
        device_behaviors = {**self._dynamic_devices.device_mac_behaviors,
                            **self._static_devices.device_mac_behaviors}
        for mac, device_placement in device_placements.items():
            device_behavior = device_behaviors.get(mac)
            if not device_behavior:
                continue

            switch_cfg = behavioral_faucet_config.get('dps', {}).get(device_placement.switch, {})
            port_cfg = switch_cfg.get('interfaces', {}).get(device_placement.port)

            if not port_cfg:
                LOGGER.warning('Switch or port not defined in faucet config for MAC %s: %s, %s',
                               mac, device_placement.switch, device_placement.port)
                continue

            vid = self._segments_to_vlans.get(device_behavior.segment)
            if not vid:
                LOGGER.warning('Device segment does not have a matching vlan: %s, %s',
                               mac, device_behavior.segment)
                continue

            port_cfg['native_vlan'] = vid
            if device_behavior.role:
                port_cfg['acls_in'] = [f'role_{device_behavior.role}']
            if self._config.tail_acl:
                port_cfg.setdefault('acls_in', []).append(self._config.tail_acl)

            dva_state = (DVAState.static if mac in self._static_devices.device_mac_behaviors
                         else DVAState.dynamic)
            self._update_vlan_state(
                device_placement.switch, device_placement.port, dva_state)

        behavioral_faucet_config['include'] = self._behavioral_include

        self._behavioral_faucet_config = behavioral_faucet_config

    def reload_structural_config(self, structural_config_file=None):
        """Reload structural config from file"""
        structural_config_file = structural_config_file or self._structural_config_file
        with open(structural_config_file) as file:
            structural_config = yaml.safe_load(file)
            self._process_structural_config(structural_config)

    def reload_acl_file(self, file_path):
        """Reload acl file"""
        with open(file_path) as acl_file:
            acls_config = yaml.safe_load(acl_file)
            self._process_acl_config(file_path, acls_config)

    def flush_behavioral_config(self, force=False):
        """Generate and write behavioral config to file"""
        if not force and self._config.faucetize_interval_sec:
            return
        self._faucetize()
        with open(self._behavioral_config_file, 'w') as file:
            yaml.dump(self._behavioral_faucet_config, file)
            LOGGER.debug('Wrote behavioral config to %s', self._behavioral_config_file)

    def flush_acl_config(self, file_path, acls_config):
        """Write acl configs to file"""
        with open(file_path, 'w') as acl_file:
            yaml.dump(acls_config, acl_file)
            LOGGER.debug('Wrote augmented included file to %s', file_path)

    def get_structural_config(self):
        """Return structural config"""
        with self._lock:
            return self._structural_faucet_config

    def get_dva_state(self, switch, port):
        """Get DVA state"""
        return self._vlan_states.get(switch, {}).get(port)


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


def load_orch_config(file):
    """Load forch config and return orchestration config"""
    forch_config = yaml_proto(file, ForchConfig)
    return forch_config.orchestration


def parse_args(raw_args):
    """Parse sys args"""
    parser = argparse.ArgumentParser(prog='faucetizer', description='faucetizer')
    parser.add_argument('-s', '--state-input', type=str, default='devices_state.yaml',
                        help='devices state input')
    parser.add_argument('-g', '--segments-vlans', type=str, default='segments-to-vlans.yaml',
                        help='segments to vlans mapping input file')
    parser.add_argument('-c', '--config-input', type=str, default='faucet.yaml',
                        help='structural faucet config input')
    parser.add_argument('-f', '--forch-config', type=str, default='forch.yaml',
                        help='unauthenticated_vlan')
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

    FORCH_CONFIG_FILE = os.path.join(FORCH_BASE_DIR, ARGS.forch_config)
    ORCH_CONFIG = load_orch_config(FORCH_CONFIG_FILE)
    STRUCTURAL_CONFIG_FILE = os.path.join(FORCH_BASE_DIR, ARGS.config_input)
    BEHAVIORAL_CONFIG_FILE = os.path.join(FAUCET_BASE_DIR, ARGS.output)

    FAUCETIZER = Faucetizer(
        ORCH_CONFIG, STRUCTURAL_CONFIG_FILE, SEGMENTS_TO_VLANS.segments_to_vlans,
        BEHAVIORAL_CONFIG_FILE)
    FAUCETIZER.reload_structural_config()

    DEVICES_STATE_FILE = os.path.join(FORCH_BASE_DIR, ARGS.state_input)
    DEVICES_STATE = load_devices_state(DEVICES_STATE_FILE)
    process_devices_state(FAUCETIZER, DEVICES_STATE)

    LOGGER.info('Processed device state and config wrote to %s', BEHAVIORAL_CONFIG_FILE)
