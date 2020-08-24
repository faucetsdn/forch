"""Unit test base class for Forch"""

import shutil
import tempfile
import unittest
import yaml

from forch.faucetizer import Faucetizer
from forch.faucet_state_collector import FaucetStateCollector
from forch.utils import dict_proto

from forch.proto.devices_state_pb2 import DevicePlacement, DeviceBehavior
from forch.proto.forch_configuration_pb2 import ForchConfig


class UnitTestBase(unittest.TestCase):
    """Base class for unit tests"""

    FORCH_CONFIG = ""
    FAUCET_STRUCTURAL_CONFIG = ""
    FAUCET_BEHAVIORAL_CONFIG = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._temp_dir = None
        self._temp_structural_config_file = None
        self._temp_behavioral_config_file = None

    def _setup_config_files(self):
        self._temp_dir = tempfile.mkdtemp()
        _, self._temp_structural_config_file = tempfile.mkstemp(dir=self._temp_dir)
        _, self._temp_behavioral_config_file = tempfile.mkstemp(dir=self._temp_dir)

        with open(self._temp_structural_config_file, 'w') as structural_config_file:
            structural_config_file.write(self.FAUCET_STRUCTURAL_CONFIG)

    def _cleanup_config_files(self):
        shutil.rmtree(self._temp_dir)


class FaucetizerTestBase(UnitTestBase):
    """Base class for Faucetizer unit tests"""

    FORCH_CONFIG = """
    orchestration:
      unauthenticated_vlan: 100
    """

    FAUCET_STRUCTURAL_CONFIG = """
    dps:
      t1sw1:
        dp_id: 111
        interfaces:
          1:
            output_only: true
          4:
            description: TESTING
            tagged_vlans: [272]
          6:
            stack: {dp: t2sw1, port: 6}
          7:
            stack: {dp: t2sw2, port: 7}
          23:
            lacp: 3
      t2sw1:
        dp_id: 121
        interfaces:
          1:
            description: HOST
            max_hosts: 1
          2:
            description: HOST
            max_hosts: 1
          6:
            stack: {dp: t1sw1, port: 6}
      t2sw2:
        dp_id: 122
        interfaces:
          1:
            description: HOST
            max_hosts: 1
          2:
            description: HOST
            max_hosts: 1
          7:
            stack: {dp: t1sw1, port: 7}
    acls:
      role_red:
        - rule:
            dl_type: 0x800
            actions:
              allow: True
      role_green:
        - rule:
            actions:
              allow: False
      tail_acl:
        - rule:
            actions:
              allow: True
    """

    FAUCET_BEHAVIORAL_CONFIG = """
    dps:
      t1sw1:
        dp_id: 111
        interfaces:
          1:
            output_only: true
          4:
            description: TESTING
            tagged_vlans: [272]
          6:
            stack: {dp: t2sw1, port: 6}
          7:
            stack: {dp: t2sw2, port: 7}
          23:
            lacp: 3
      t2sw1:
        dp_id: 121
        interfaces:
          1:
            description: HOST
            max_hosts: 1
            native_vlan: 100
          2:
            description: HOST
            max_hosts: 1
            native_vlan: 100
          6:
            stack: {dp: t1sw1, port: 6}
      t2sw2:
        dp_id: 122
        interfaces:
          1:
            description: HOST
            max_hosts: 1
            native_vlan: 100
          2:
            description: HOST
            max_hosts: 1
            native_vlan: 100
          7:
            stack: {dp: t1sw1, port: 7}
    acls:
      role_red:
        - rule:
            cookie: 1
            dl_type: 2048
            actions:
              allow: True
      role_green:
        - rule:
            cookie: 2
            actions:
              allow: False
      tail_acl:
        - rule:
            cookie: 3
            actions:
              allow: True
    """

    SEGMENTS_TO_VLANS = """
    segments_to_vlans:
      SEG_A: 200
      SEG_B: 300
      SEG_C: 400
      SEG_X: 1500
      SEG_Y: 1600
      SEG_Z: 1700
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._faucetizer = None
        self._segments_vlans_file = None

    def _setup_config_files(self):
        super()._setup_config_files()

        _, self._segments_vlans_file = tempfile.mkstemp(dir=self._temp_dir)
        with open(self._segments_vlans_file, 'w') as segments_vlans_file:
            segments_vlans_file.write(self.SEGMENTS_TO_VLANS)

    def _initialize_faucetizer(self):
        forch_config = dict_proto(yaml.safe_load(self.FORCH_CONFIG), ForchConfig)

        self._faucetizer = Faucetizer(
            forch_config.orchestration, self._temp_structural_config_file,
            self._temp_behavioral_config_file)
        self._faucetizer.reload_structural_config()
        self._faucetizer.reload_segments_to_vlans(self._segments_vlans_file)

    def _process_device_placement(self, placement_tuple):
        self._faucetizer.process_device_placement(
            placement_tuple[0], dict_proto(placement_tuple[1], DevicePlacement),
            placement_tuple[2])

    def _process_device_behavior(self, behavior_tuple):
        self._faucetizer.process_device_behavior(
            behavior_tuple[0], dict_proto(behavior_tuple[1], DeviceBehavior),
            behavior_tuple[2])

    def _update_port_config(
            self, behavioral_config, switch, port, native_vlan=None, role=None, tail_acl=None,
            tagged_vlans=None):
        port_config = behavioral_config['dps'][switch]['interfaces'][port]
        port_config['native_vlan'] = native_vlan
        if role:
            port_config['acls_in'] = [f'role_{role}']
        if tail_acl:
            port_config.setdefault('acls_in', []).append(tail_acl)
        if tagged_vlans:
            port_config['tagged_vlans'] = tagged_vlans

    def _verify_behavioral_config(self, expected_behavioral_config):
        with open(self._temp_behavioral_config_file) as temp_behavioral_config_file:
            faucetizer_behavioral_config = yaml.safe_load(temp_behavioral_config_file)
        self.assertEqual(faucetizer_behavioral_config, expected_behavioral_config)

    def setUp(self):
        """setup fixture for each test method"""
        self._setup_config_files()
        self._initialize_faucetizer()

    def tearDown(self):
        """cleanup after each test method finishes"""
        self._faucetizer = None
        self._cleanup_config_files()


class FaucetStateCollectorTestBase(UnitTestBase):
    """Base class for Faucetizer unit tests"""

    FORCH_CONFIG = """
    event_client:
      stack_topo_change_coalesce_sec: 15
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._faucet_state_collector = None

    def setUp(self):
        """setup fixture for each test method"""
        self._initialize_state_collector()

    def tearDown(self):
        """cleanup after each test method finishes"""
        self._faucet_state_collector = None

    def _initialize_state_collector(self):
        forch_config = dict_proto(yaml.safe_load(self.FORCH_CONFIG), ForchConfig)
        self._faucet_state_collector = FaucetStateCollector(forch_config,
                                                            is_faucetizer_enabled=False)
