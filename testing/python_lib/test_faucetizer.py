"""Unit tests for Faucetizer"""

import shutil
import tempfile
import unittest
import yaml

from forch.faucetizer import Faucetizer
from forch.proto.forch_configuration_pb2 import OrchestrationConfig
from forch.proto.devices_state_pb2 import DevicePlacement, DeviceBehavior
from forch.utils import dict_proto, str_proto


class FaucetizerTestBase(unittest.TestCase):
    """Base class for Faucetizer unit tests"""

    ORCH_CONFIG = ''
    FAUCET_STRUCTURAL_CONFIG = ''
    FAUCET_BEHAVIORAL_CONFIG = ''
    SEGMENTS_TO_VLANS = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._faucetizer = None
        self._orch_config = None
        self._temp_dir = None
        self._temp_structural_config_file = None
        self._temp_behavioral_config_file = None
        self._temp_segments_vlans_file = None

    def _setup_config_files(self):
        self._temp_dir = tempfile.mkdtemp()
        _, self._temp_structural_config_file = tempfile.mkstemp(dir=self._temp_dir)
        _, self._temp_behavioral_config_file = tempfile.mkstemp(dir=self._temp_dir)
        with open(self._temp_structural_config_file, 'w') as structural_config_file:
            structural_config_file.write(self.FAUCET_STRUCTURAL_CONFIG)

        if self.SEGMENTS_TO_VLANS:
            _, self._temp_segments_vlans_file = tempfile.mkstemp(dir=self._temp_dir)
            with open(self._temp_segments_vlans_file, 'w') as segments_vlans_file:
                segments_vlans_file.write(self.SEGMENTS_TO_VLANS)

    def _cleanup_config_files(self):
        shutil.rmtree(self._temp_dir)

    def _initialize_faucetizer(self):
        self._orch_config = str_proto(self.ORCH_CONFIG, OrchestrationConfig)

        self._faucetizer = Faucetizer(
            self._orch_config, self._temp_structural_config_file,
            self._temp_behavioral_config_file)
        self._faucetizer.reload_structural_config()
        if self._temp_segments_vlans_file:
            self._faucetizer.reload_segments_to_vlans(self._temp_segments_vlans_file)

    def _process_device_placement(self, placement_tuple):
        self._faucetizer.process_device_placement(
            placement_tuple[0], dict_proto(placement_tuple[1], DevicePlacement),
            placement_tuple[2])

    def _process_device_behavior(self, behavior_tuple):
        self._faucetizer.process_device_behavior(
            behavior_tuple[0], dict_proto(behavior_tuple[1], DeviceBehavior),
            behavior_tuple[2])

    def _update_port_config(self, behavioral_config, **kwargs):
        port_config = behavioral_config['dps'][kwargs['switch']]['interfaces'][kwargs['port']]
        port_config['native_vlan'] = kwargs.get('vlan')
        if 'role' in kwargs:
            port_config['acls_in'] = [f'role_{kwargs["role"]}']
        if 'tail_acl' in kwargs:
            port_config.setdefault('acls_in', []).append(kwargs['tail_acl'])

    def _get_base_behavioral_config(self):
        base_behavioral_config = yaml.safe_load(self.FAUCET_BEHAVIORAL_CONFIG)
        if self._orch_config.unauthenticated_vlan:
            vlans_config = base_behavioral_config.setdefault('vlans', {})
            vlans_config[self._orch_config.unauthenticated_vlan] = {
                'acls_in': [f'uniform_{self._orch_config.unauthenticated_vlan}'],
                'description': 'unauthenticated VLAN'
            }
        return base_behavioral_config

    def _verify_behavioral_config(self, expected_behavioral_config):
        with open(self._temp_behavioral_config_file) as temp_behavioral_config_file:
            faucetizer_behavioral_config = yaml.safe_load(temp_behavioral_config_file)
        self.assertEqual(faucetizer_behavioral_config, expected_behavioral_config)


class FaucetizerSimpleTestCase(FaucetizerTestBase):
    """Test basic functionality of Faucetizer"""

    ORCH_CONFIG = """
    """

    FAUCET_STRUCTURAL_CONFIG = """
    dps:
      t2sw1:
        dp_id: 121
        interfaces:
          1:
            description: HOST
            max_hosts: 1
          2:
            description: HOST
            max_hosts: 1
    """

    FAUCET_BEHAVIORAL_CONFIG = """
    dps:
      t2sw1:
        dp_id: 121
        interfaces:
          1:
            description: HOST
            max_hosts: 1
          2:
            description: HOST
            max_hosts: 1
    """

    def setUp(self):
        """setup fixture for each test method"""
        self._setup_config_files()
        self._initialize_faucetizer()

    def tearDown(self):
        """cleanup after each test method finishes"""
        self._faucetizer = None
        self._cleanup_config_files()

    def test_faucetize_simple(self):
        """test normal faucetize behavior"""
        self._faucetizer.reload_structural_config()

        expected_config = self._get_base_behavioral_config()
        self._verify_behavioral_config(expected_config)


class FaucetizerBehaviorBaseTestCase(FaucetizerTestBase):
    """Base test case to test Faucetizer behavior"""

    FAUCET_STRUCTURAL_CONFIG = """
    dps:
      t1sw1:
        dp_id: 111
        interfaces:
          1:
            output_only: true
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
      uniform_100:
        - rule:
            actions:
              allow: False
    """

    FAUCET_BEHAVIORAL_CONFIG = """
    dps:
      t1sw1:
        dp_id: 111
        interfaces:
          1:
            output_only: true
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
      uniform_100:
        - rule:
            cookie: 4
            actions:
              allow: False
    """

    SEGMENTS_TO_VLANS = """
    segments_to_vlans:
      SEG_A: 200
      SEG_B: 300
      SEG_C: 400
    """

    def setUp(self):
        """setup fixture for each test method"""
        self._setup_config_files()
        self._initialize_faucetizer()

    def tearDown(self):
        """cleanup after each test method finishes"""
        self._faucetizer = None
        self._cleanup_config_files()


class FaucetizerBehaviorTestCase(FaucetizerBehaviorBaseTestCase):
    """Test Faucetizer's behavior after several iterations of device information processing"""

    ORCH_CONFIG = """
    unauthenticated_vlan: 100
    tail_acl: 'tail_acl'
    """

    def test_devices_learned_and_authenticated(self):
        """devices with different combinations of static and dynamic info"""
        self._faucetizer.reload_structural_config()

        placements = [
            # mocking static placements
            ('02:0A:00:00:00:01', {'switch': 't2sw1', 'port': 1, 'connected': True}, True),
            ('02:0b:00:00:00:02', {'switch': 't2sw1', 'port': 2, 'connected': True}, True),
            # devices dynamically learned
            ('02:0a:00:00:00:01', {'switch': 't2sw2', 'port': 2, 'connected': True}, False),
            ('02:0c:00:00:00:03', {'switch': 't2sw2', 'port': 1, 'connected': True}, False),
            ('02:0D:00:00:00:04', {'switch': 't2sw2', 'port': 2, 'connected': True}, False),
            # devices expired
            ('02:0a:00:00:00:01', {'switch': 't2sw2', 'port': 2, 'connected': False}, False),
            ('02:0c:00:00:00:03', {'switch': 't2sw2', 'port': 1, 'connected': False}, False)
        ]

        behaviors = [
            # mocking static behaviors
            ('02:0a:00:00:00:01', {'segment': 'SEG_A', 'role': 'red'}, True),
            ('02:0c:00:00:00:03', {'segment': 'SEG_C'}, True),
            # devices authenticated
            ('02:0B:00:00:00:02', {'segment': 'SEG_B', 'role': 'green'}, False),
            ('02:0c:00:00:00:03', {'segment': 'SEG_A', 'role': 'black'}, False),
            ('02:0D:00:00:00:04', {'segment': 'SEG_X', 'role': 'red'}, False)
        ]

        # process static device info
        self._process_device_placement(placements[0])
        self._process_device_placement(placements[1])
        self._process_device_behavior(behaviors[0])
        self._process_device_behavior(behaviors[1])

        # process dynamic device info
        self._process_device_behavior(behaviors[2])
        self._process_device_placement(placements[2])
        self._process_device_placement(placements[3])
        self._process_device_placement(placements[4])
        self._process_device_behavior(behaviors[4])
        self._process_device_behavior(behaviors[3])

        expected_config = self._get_base_behavioral_config()
        self._update_port_config(expected_config, switch='t2sw1', port=1, native_vlan=200,
                                 role='red', tail_acl='tail_acl')
        self._update_port_config(expected_config, switch='t2sw1', port=2, native_vlan=300,
                                 role='green', tail_acl='tail_acl')
        self._update_port_config(expected_config, switch='t2sw2', port=1, native_vlan=200,
                                 tail_acl='tail_acl')
        self._update_port_config(expected_config, switch='t2sw2', port=2, native_vlan=100,
                                 tail_acl='tail_acl')
        self._verify_behavioral_config(expected_config)

        # device expired
        self._process_device_placement(placements[5])
        self._process_device_placement(placements[6])

        expected_config = self._get_base_behavioral_config()
        self._update_port_config(expected_config, switch='t2sw1', port=1, native_vlan=200,
                                 role='red', tail_acl='tail_acl')
        self._update_port_config(expected_config, switch='t2sw1', port=2, native_vlan=300,
                                 role='green', tail_acl='tail_acl')
        self._update_port_config(expected_config, switch='t2sw2', port=1, native_vlan=100,
                                 tail_acl='tail_acl')
        self._update_port_config(expected_config, switch='t2sw2', port=2, native_vlan=100,
                                 tail_acl='tail_acl')
        self._verify_behavioral_config(expected_config)


class FaucetizerBehaviorWithoutTailACLTestCase(FaucetizerBehaviorBaseTestCase):
    """Test Faucetizer's behavior with no tail_acl setting in Forch config"""

    ORCH_CONFIG = """
    unauthenticated_vlan: 100
    """

    def test_devices_learned_and_authenticated(self):
        """devices with different combinations of static and dynamic info"""
        self._faucetizer.reload_structural_config()

        placements = [
            # static placement
            ('02:0A:00:00:00:01', {'switch': 't2sw1', 'port': 1, 'connected': True}, True),
            # dynamic placement
            ('02:0a:00:00:00:02', {'switch': 't2sw1', 'port': 2, 'connected': True}, False),
        ]

        behaviors = [
            # static behavior
            ('02:0a:00:00:00:02', {'segment': 'SEG_B'}, True),
            # dynamic behavior with non existent role
            ('02:0a:00:00:00:01', {'segment': 'SEG_A', 'role': 'black'}, False),
        ]

        # process static device info
        self._process_device_placement(placements[0])
        self._process_device_behavior(behaviors[1])

        # process dynamic device info
        self._process_device_placement(placements[1])
        self._process_device_behavior(behaviors[0])

        expected_config = self._get_base_behavioral_config()
        self._update_port_config(
            expected_config, switch='t2sw1', port=1, native_vlan=200)
        self._update_port_config(
            expected_config, switch='t2sw1', port=2, native_vlan=300)
        self._verify_behavioral_config(expected_config)


class FaucetizerMissingTailACLDefinitionTestCase(FaucetizerTestBase):
    """Test case where no ACL is defined for the tail_acl specified in forch.yaml"""

    ORCH_CONFIG = """
    unauthenticated_vlan: 100
    tail_acl: 'non_existing_acl'
    """

    FAUCET_STRUCTURAL_CONFIG = """
    dps:
      t2sw1:
        dp_id: 121
        interfaces:
          1:
            description: HOST
            max_hosts: 1
    acls:
      tail_acl:
        - rule:
            actions:
              allow: True
    """

    def test_no_tail_acl_definition(self):
        """test faucetizer behavior when no ACL is defined for tail_acl"""
        self._setup_config_files()
        self.assertRaises(Exception, self._initialize_faucetizer)


if __name__ == '__main__':
    unittest.main()
