"""Collect Faucet information and generate ACLs"""

import abc
import argparse
import copy
import os
import shutil
import sys
import tempfile
import threading
import yaml

from forch.utils import get_logger, yaml_proto

from forch.proto.devices_state_pb2 import DevicesState, SegmentsToVlans
from forch.proto.devices_state_pb2 import DevicePlacement, DeviceBehavior
from forch.proto.forch_configuration_pb2 import ForchConfig
from forch.proto.shared_constants_pb2 import DVAState, PortType

INCLUDE_FILE_SUFFIX = '_augmented'
SEQUESTER_PORT_DESCRIPTION_DEFAULT = 'TESTING'
DEVICE_BEHAVIOR = 'device_behavior'
DEVICE_TYPE = 'device_type'
STATIC_DEVICE = 'static'
DYNAMIC_DEVICE = 'dynamic'


class DeviceStateManager(abc.ABC):
    """Interface collecting the methods that manage device state"""

    @abc.abstractmethod
    def process_device_placement(self, eth_src, placement, static=False):
        """process device placement"""

    @abc.abstractmethod
    def process_device_behavior(self, eth_src, behavior, static=False):
        """process device behavior"""

    @abc.abstractmethod
    def get_vlan_from_segment(self, segment):
        """get vlan from segment"""


class Faucetizer(DeviceStateManager):
    """Collect Faucet information and generate ACLs"""
    # pylint: disable=too-many-arguments
    def __init__(self, orch_config, structural_config_file, behavioral_config_file,
                 reregister_include_file_handlers=None, reset_faucet_config_writing_time=None):
        self._static_devices = DevicesState()
        self._dynamic_devices = DevicesState()
        self._device_behaviors = {}
        self._testing_device_vlans = {}
        self._acl_configs = {}
        self._vlan_states = {}
        self._segments_to_vlans = {}
        self._structural_faucet_config = None
        self._behavioral_faucet_config = None
        self._behavioral_include = None
        self._next_cookie = None
        self._config = orch_config
        self._structural_config_file = structural_config_file
        self._behavioral_config_file = behavioral_config_file
        self._forch_config_dir = os.path.dirname(self._structural_config_file)
        self._faucet_config_dir = os.path.dirname(self._behavioral_config_file)
        self._all_testing_vlans = None
        self._available_testing_vlans = None
        self._watched_include_files = []
        self._reregister_include_file_handlers = reregister_include_file_handlers
        self._reset_faucet_config_writing_time = reset_faucet_config_writing_time
        self._lock = threading.RLock()
        self._logger = get_logger('faucetizer')

        self._validate_and_initialize_config()

    def process_device_placement(self, eth_src, placement, static=False):
        """Process device placement"""
        if not placement.switch or not placement.port:
            raise Exception(f'Incomplete placement for {eth_src}: {placement}')

        devices_state = self._static_devices if static else self._dynamic_devices
        device_type = "static" if static else "dynamic"
        eth_src = eth_src.lower()

        with self._lock:
            device_placements = devices_state.device_mac_placements
            if placement.connected:
                device_placement = device_placements.setdefault(eth_src, DevicePlacement())
                device_placement.CopyFrom(placement)
                self._logger.info(
                    'Received %s placement: %s, %s, %s',
                    device_type, eth_src, device_placement.switch, device_placement.port)
            else:
                removed = device_placements.pop(eth_src, None)
                if removed:
                    self._logger.info(
                        'Removed %s placement: %s, %s, %s',
                        device_type, eth_src, removed.switch, removed.port)

            self.flush_behavioral_config()

    def process_device_behavior(self, eth_src, behavior, static=False):
        """Process device behavior"""
        eth_src = eth_src.lower()
        device_type = STATIC_DEVICE if static else DYNAMIC_DEVICE

        with self._lock:
            if behavior.segment:
                behavior_map = self._device_behaviors.setdefault(eth_src, {})
                behavior_map[DEVICE_TYPE] = device_type
                device_behavior = behavior_map.setdefault(DEVICE_BEHAVIOR, DeviceBehavior())
                device_behavior.CopyFrom(behavior)
                self._logger.info(
                    'Received %s behavior: %s, %s (%s), %s',
                    device_type, eth_src, device_behavior.segment,
                    self.get_vlan_from_segment(behavior.segment), device_behavior.role)
            else:
                removed = self._device_behaviors.pop(eth_src, None)
                if removed:
                    removed_behavior = removed[DEVICE_BEHAVIOR]
                    self._logger.info(
                        'Removed %s behavior: %s, %s, %s',
                        device_type, eth_src, removed_behavior.segment, removed_behavior.role)

            self.flush_behavioral_config()

    def _process_structural_config(self, faucet_config):
        """Process faucet config when structural faucet config changes"""
        with self._lock:
            self._structural_faucet_config = copy.deepcopy(faucet_config)
            self._acl_configs.clear()

            self._next_cookie = 1
            behavioral_include = []
            new_watched_include_files = []

            for include_file_name in self._structural_faucet_config.get('include', []):
                include_file_path = os.path.join(self._forch_config_dir, include_file_name)
                self.reload_include_file(include_file_path)
                behavioral_include.append(self._augment_include_file_name(include_file_name))
                new_watched_include_files.append(include_file_path)

            structural_acls_config = copy.deepcopy(self._structural_faucet_config.get('acls'))
            self._augment_acls_config(structural_acls_config, self._structural_config_file, )

            tail_acl_name = self._config.tail_acl
            if tail_acl_name and not self._has_acl(tail_acl_name):
                raise Exception('No ACL is defined for tail ACL %s' % tail_acl_name)

            self._behavioral_include = behavioral_include

            if not self._config.faucetize_interval_sec and self._reregister_include_file_handlers:
                self._reregister_include_file_handlers(
                    self._watched_include_files, new_watched_include_files)
            self._watched_include_files = new_watched_include_files

            self.flush_behavioral_config()

    def _yaml_atomic_dump(self, config, file_path):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_file = os.path.join(tmp_dir, os.path.basename(file_path))
            with open(tmp_file, 'w') as fd:
                yaml.dump(config, fd)
            shutil.move(tmp_file, file_path)

    def _augment_acls_config(self, acls_config, file_path):
        if not acls_config:
            return

        if not self._next_cookie:
            raise Exception('Cookie is not initialized')

        with self._lock:
            for rule_list in acls_config.values():
                for rule_map in rule_list:
                    if 'rule' in rule_map:
                        rule_map['rule']['cookie'] = self._next_cookie
                        self._next_cookie += 1

            self._acl_configs[file_path] = copy.deepcopy(acls_config)

    def _augment_include_file_name(self, file_name):
        base_file_name, ext = os.path.splitext(file_name)
        return base_file_name + INCLUDE_FILE_SUFFIX + ext

    def _validate_and_initialize_config(self):
        if self._config.sequester_config.segment:
            starting_vlan = self._config.sequester_config.vlan_start
            ending_vlan = self._config.sequester_config.vlan_end
            if not starting_vlan or not ending_vlan:
                raise Exception(
                    f'Starting or ending testing VLAN missing: {starting_vlan}, {ending_vlan}')

            self._all_testing_vlans = set(range(starting_vlan, ending_vlan+1))

    def _get_port_type(self, port_cfg):
        sequester_port_description = (self._config.sequester_config.port_description or
                                      SEQUESTER_PORT_DESCRIPTION_DEFAULT)
        if sequester_port_description in port_cfg.get('description', ""):
            return PortType.testing
        non_access_port_properties = ['stack', 'lacp', 'output_only', 'tagged_vlans']
        port_properties = [
            property for property in non_access_port_properties if property in port_cfg]
        return PortType.access if len(port_properties) == 0 else PortType.other

    def _calculate_available_tesing_vlans(self):
        if not self._config.sequester_config.segment:
            return None
        operational_vlans = set(self._segments_to_vlans.values())
        used_testing_vlans = set(self._testing_device_vlans.values())
        return self._all_testing_vlans - operational_vlans - used_testing_vlans

    def _update_vlan_state(self, switch, port, state):
        self._vlan_states.setdefault(switch, {})[port] = state

    def _initialize_host_ports(self):
        if not self._structural_faucet_config:
            raise Exception('Structural faucet configuration not provided')

        behavioral_faucet_config = copy.deepcopy(self._structural_faucet_config)

        for switch, switch_map in behavioral_faucet_config.get('dps', {}).items():
            for port, port_map in switch_map.get('interfaces', {}).items():
                if not self._get_port_type(port_map) == PortType.access:
                    continue
                if self._config.unauthenticated_vlan:
                    port_map['native_vlan'] = self._config.unauthenticated_vlan
                    self._update_vlan_state(switch, port, DVAState.unauthenticated)

        return behavioral_faucet_config

    def _finalize_host_ports_config(self, behavioral_faucet_config, testing_port_vlans):
        testing_port_configured = False
        for switch_map in behavioral_faucet_config.get('dps', {}).values():
            for port_map in switch_map.get('interfaces', {}).values():
                port_type = self._get_port_type(port_map)
                if port_type == PortType.testing and testing_port_vlans:
                    port_map.setdefault('tagged_vlans', []).extend(testing_port_vlans)
                    testing_port_configured = True
                if self._get_port_type(port_map) == PortType.access and self._config.tail_acl:
                    port_map.setdefault('acls_in', []).append(self._config.tail_acl)

        if testing_port_vlans and not testing_port_configured:
            self._logger.error('No testing port found')

    def _has_acl(self, acl_name):
        for acl_config in self._acl_configs.values():
            if acl_name in acl_config:
                return True
        return False

    def _calculate_vlan_id(self, device_mac, device_behavior, available_testing_vlans,
                           testing_port_vlans):
        device_segment = device_behavior.segment
        sequester_segment = self._config.sequester_config.segment
        vid = None

        if sequester_segment and device_segment == sequester_segment:
            if device_mac not in self._testing_device_vlans and not available_testing_vlans:
                self._logger.error(
                    'No available testing VLANs. Used %d VLANs', len(self._testing_device_vlans))
            else:
                if device_mac not in self._testing_device_vlans:
                    vid = available_testing_vlans.pop()
                    self._testing_device_vlans[device_mac] = vid
                    self._logger.info('Device %s is sequestered on vlan %d', device_mac, vid)
                testing_port_vlans.add(self._testing_device_vlans[device_mac])
        elif device_segment in self._segments_to_vlans:
            vid = self._segments_to_vlans[device_segment]
        else:
            self._logger.warning(
                'Device segment does not have a matching vlan: %s, %s', device_mac, device_segment)

        return vid

    def _update_device_dva_state(self, device_placement, device_behavior, device_type):
        if device_type == STATIC_DEVICE:
            dva_state = DVAState.static
        elif device_behavior.segment == self._config.sequester_config.segment:
            dva_state = DVAState.sequestered
        elif device_behavior.segment in self._segments_to_vlans:
            dva_state = DVAState.operational

        if dva_state:
            self._update_vlan_state(device_placement.switch, device_placement.port, dva_state)

    def _update_vlans_config(self, behavioral_faucet_config):
        vlans_config = behavioral_faucet_config.setdefault('vlans', {})
        if self._config.unauthenticated_vlan not in vlans_config:
            vlan_acl = f'uniform_{self._config.unauthenticated_vlan}'
            if next((acls for acls in self._acl_configs.values() if vlan_acl in acls), None):
                vlan_config = {
                    'acls_in': [f'uniform_{self._config.unauthenticated_vlan}'],
                    'description': 'unauthenticated VLAN'
                }
                vlans_config[self._config.unauthenticated_vlan] = vlan_config
            else:
                self._logger.error('VLAN ACL is not defined: %s', vlan_acl)
        else:
            self._logger.warning(
                'Unauthenticated VLAN is already defined in structural config: %s',
                self._config.unauthenticated_vlan)

    def _faucetize(self):
        behavioral_faucet_config = self._initialize_host_ports()

        available_testing_vlans = self._calculate_available_tesing_vlans()
        testing_port_vlans = set()

        # static information of a device should overwrite the corresponding dynamic one
        device_placements = {**self._dynamic_devices.device_mac_placements,
                             **self._static_devices.device_mac_placements}
        for mac, device_placement in device_placements.items():
            behavior_map = self._device_behaviors.get(mac, {})
            device_behavior = behavior_map.get(DEVICE_BEHAVIOR)
            device_type = behavior_map.get(DEVICE_TYPE)
            if not device_behavior:
                continue

            switch_cfg = behavioral_faucet_config.get('dps', {}).get(device_placement.switch, {})
            port_cfg = switch_cfg.get('interfaces', {}).get(device_placement.port)

            if not port_cfg:
                self._logger.warning(
                    'Switch or port not defined in faucet config for MAC %s: %s, %s',
                    mac, device_placement.switch, device_placement.port)
                continue

            vid = self._calculate_vlan_id(mac, device_behavior, available_testing_vlans,
                                          testing_port_vlans)
            self._logger.info('Placing %s into vlan %s', mac, vid)
            if not vid:
                continue
            port_cfg['native_vlan'] = vid

            if device_behavior.role:
                acl_name = f'role_{device_behavior.role}'
                if self._has_acl(acl_name):
                    port_cfg['acls_in'] = [acl_name]
                else:
                    self._logger.error('No ACL defined for role %s', device_behavior.role)

            self._update_device_dva_state(device_placement, device_behavior, device_type)

        self._finalize_host_ports_config(behavioral_faucet_config, testing_port_vlans)

        if self._behavioral_include:
            behavioral_faucet_config['include'] = self._behavioral_include
        if self._config.unauthenticated_vlan:
            self._update_vlans_config(behavioral_faucet_config)

        structural_acls_config = self._acl_configs.get(self._structural_config_file)
        if structural_acls_config:
            behavioral_faucet_config['acls'] = structural_acls_config

        self._behavioral_faucet_config = behavioral_faucet_config

    def reload_structural_config(self, structural_config_file=None):
        """Reload structural config from file"""
        structural_config_file = structural_config_file or self._structural_config_file
        with open(structural_config_file) as file:
            structural_config = yaml.safe_load(file)
            self._process_structural_config(structural_config)

    def reload_and_flush_gauge_config(self, gauge_config_file):
        """Reload gauge config file and rewrite to faucet config directory"""
        with open(gauge_config_file) as file:
            gauge_config = yaml.safe_load(file)

        gauge_file_name = os.path.split(gauge_config_file)[1]
        new_gauge_file_path = os.path.join(self._faucet_config_dir, gauge_file_name)
        self._yaml_atomic_dump(gauge_config, new_gauge_file_path)
        self._logger.debug('Wrote Gauge configuration file to %s', new_gauge_file_path)

    def reload_include_file(self, file_path):
        """Reload include file"""
        with open(file_path) as file:
            include_config = yaml.safe_load(file)
            if not include_config:
                self._logger.warning('Included file is empty: %s', file_path)
                return

            acls_config = include_config.get('acls')
            self._augment_acls_config(acls_config, file_path)

            relative_include_path = os.path.relpath(file_path, start=self._forch_config_dir)
            new_file_path = self._augment_include_file_name(relative_include_path)
            self.flush_include_config(new_file_path, include_config)

    def reload_segments_to_vlans(self, file_path):
        """Reload file that contains the mappings from segments to vlans"""
        self._segments_to_vlans = yaml_proto(file_path, SegmentsToVlans).segments_to_vlans

        operational_vlans = set(self._segments_to_vlans.values())
        if self._all_testing_vlans and self._all_testing_vlans & operational_vlans:
            self._logger.error(
                'Testing VLANs has intersection with operational VLANs: %s',
                self._all_testing_vlans & operational_vlans)

        self.flush_behavioral_config()

    def clear_static_placements(self):
        """Remove all static placements in memory"""
        self._static_devices.ClearField('device_mac_placements')

    def clear_static_behaviors(self):
        """Remove all static behaviors in memory"""
        self._static_devices.ClearField('device_mac_behaviors')

    def flush_behavioral_config(self, force=False):
        """Generate and write behavioral config to file"""
        if not force and self._config.faucetize_interval_sec:
            return
        self._faucetize()
        self._yaml_atomic_dump(self._behavioral_faucet_config, self._behavioral_config_file)
        self._logger.debug('Wrote behavioral config to %s', self._behavioral_config_file)

        if self._reset_faucet_config_writing_time:
            self._reset_faucet_config_writing_time()

    def flush_include_config(self, include_file_name, include_config):
        """Write include configs to file"""
        faucet_include_file_path = os.path.join(self._faucet_config_dir, include_file_name)
        os.makedirs(os.path.dirname(faucet_include_file_path), exist_ok=True)
        self._yaml_atomic_dump(include_config, faucet_include_file_path)
        self._logger.debug('Wrote augmented included file to %s', faucet_include_file_path)

    def get_structural_config(self):
        """Return structural config"""
        with self._lock:
            return self._structural_faucet_config

    def get_dva_state(self, switch, port):
        """Get DVA state"""
        with self._lock:
            return self._vlan_states.get(switch, {}).get(port)

    def get_vlan_from_segment(self, segment):
        """Get VLAN id from segment"""
        return self._segments_to_vlans.get(segment)


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
    LOGGER = get_logger('faucetizer', stdout=True)
    FORCH_BASE_DIR = os.getenv('FORCH_CONFIG_DIR')
    FAUCET_BASE_DIR = os.getenv('FAUCET_CONFIG_DIR')
    ARGS = parse_args(sys.argv[1:])

    FORCH_CONFIG_FILE = os.path.join(FORCH_BASE_DIR, ARGS.forch_config)
    ORCH_CONFIG = load_orch_config(FORCH_CONFIG_FILE)
    STRUCTURAL_CONFIG_FILE = os.path.join(FORCH_BASE_DIR, ARGS.config_input)
    BEHAVIORAL_CONFIG_FILE = os.path.join(FAUCET_BASE_DIR, ARGS.output)
    SEGMENTS_VLANS_FILE = os.path.join(FORCH_BASE_DIR, ARGS.segments_vlans)

    FAUCETIZER = Faucetizer(
        ORCH_CONFIG, STRUCTURAL_CONFIG_FILE, BEHAVIORAL_CONFIG_FILE)
    FAUCETIZER.reload_structural_config()
    FAUCETIZER.reload_segments_to_vlans(SEGMENTS_VLANS_FILE)

    DEVICES_STATE_FILE = os.path.join(FORCH_BASE_DIR, ARGS.state_input)
    DEVICES_STATE = load_devices_state(DEVICES_STATE_FILE)
    process_devices_state(FAUCETIZER, DEVICES_STATE)

    LOGGER.info('Processed device state and config wrote to %s', BEHAVIORAL_CONFIG_FILE)
