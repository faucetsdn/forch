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
    SEGMENTS_TO_VLANS = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._faucetizer = None
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

    def _initialize_faucetizer(self):
        orch_config = str_proto(self.ORCH_CONFIG, OrchestrationConfig)

        self._faucetizer = Faucetizer(
            orch_config, self._temp_structural_config_file, self.SEGMENTS_TO_VLANS,
            self._temp_behavioral_config_file)
        self._faucetizer.reload_structural_config()

    def _process_device_placement(self, placement_tuple):
        self._faucetizer.process_device_placement(
            placement_tuple[0], dict_proto(placement_tuple[1], DevicePlacement),
            placement_tuple[2])

    def _process_device_behavior(self, behavior_tuple):
        self._faucetizer.process_device_behavior(
            behavior_tuple[0], dict_proto(behavior_tuple[1], DeviceBehavior),
            behavior_tuple[2])

    def _update_port_config(self, behavioral_config, switch, port, vlan, role):
        port_config = behavioral_config['dps'][switch]['interfaces'][port]
        port_config['native_vlan'] = vlan
        port_config['acls_in'] = [f'role_{role}', 'tail_acl']

    def _verify_behavioral_config(self, expected_behavioral_config):
        with open(self._temp_behavioral_config_file) as temp_behavioral_config_file:
            faucetizer_behavioral_config = yaml.safe_load(temp_behavioral_config_file)
        self.assertEqual(faucetizer_behavioral_config, expected_behavioral_config)


class FaucetizerSimpleTestCase(FaucetizerTestBase):
    """Test basic functionality of Faucetizer"""

    ORCH_CONFIG = 'unauthenticated_vlan: 100'

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
        self._faucetizer.flush_behavioral_config(force=True)

        expected_behavioral_config_str = """
        dps:
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
        include: []
        """
        self._verify_behavioral_config(yaml.safe_load(expected_behavioral_config_str))


class FaucetizerBehaviorTestCase(FaucetizerTestBase):
    """Test Faucetizer's behavior after several iterations of device information processing"""

    ORCH_CONFIG = 'unauthenticated_vlan: 100'

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
    include: []
    """

    SEGMENTS_TO_VLANS = {
        'SEG_A': 200,
        'SEG_B': 300,
        'SEG_C': 400
    }

    def setUp(self):
        """setup fixture for each test method"""
        self._setup_config_files()
        self._initialize_faucetizer()

    def tearDown(self):
        """cleanup after each test method finishes"""
        self._faucetizer = None
        self._cleanup_config_files()

    def test_devices_learned_and_authenticated(self):
        """devices with different combinations of static and dynamic info"""
        self._faucetizer.reload_structural_config()

        placements = [
            # mocking static placements
            ('02:00:00:00:00:01', {'switch': 't2sw1', 'port': 1, 'connected': True}, True),
            ('02:00:00:00:00:02', {'switch': 't2sw1', 'port': 2, 'connected': True}, True),
            # devices dynamically learned
            ('02:00:00:00:00:01', {'switch': 't2sw2', 'port': 2, 'connected': True}, False),
            ('02:00:00:00:00:03', {'switch': 't2sw2', 'port': 1, 'connected': True}, False),
            # devices expired
            ('02:00:00:00:00:01', {'switch': 't2sw2', 'port': 2, 'connected': False}, False),
            ('02:00:00:00:00:03', {'switch': 't2sw2', 'port': 1, 'connected': False}, False)
        ]

        behaviors = [
            # mocking static behaviors
            ('02:00:00:00:00:01', {'segment': 'SEG_A', 'role': 'red'}, True),
            ('02:00:00:00:00:03', {'segment': 'SEG_C', 'role': 'blue'}, True),
            # devices authenticated
            ('02:00:00:00:00:02', {'segment': 'SEG_B', 'role': 'green'}, False),
            ('02:00:00:00:00:03', {'segment': 'SEG_A', 'role': 'yellow'}, False)
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
        self._process_device_behavior(behaviors[3])

        expected_behavioral_config = yaml.safe_load(self.FAUCET_BEHAVIORAL_CONFIG)
        self._update_port_config(expected_behavioral_config, 't2sw1', 1, 200, 'red')
        self._update_port_config(expected_behavioral_config, 't2sw1', 2, 300, 'green')
        self._update_port_config(expected_behavioral_config, 't2sw2', 1, 400, 'green')
        self._verify_behavioral_config(expected_behavioral_config)

        # device expired
        self._process_device_placement(placements[4])
        self._process_device_placement(placements[5])

        expected_behavioral_config = yaml.safe_load(self.FAUCET_BEHAVIORAL_CONFIG)
        self._update_port_config(expected_behavioral_config, 't2sw1', 1, 200, 'red')
        self._update_port_config(expected_behavioral_config, 't2sw1', 2, 300, 'green')
        self._verify_behavioral_config(yaml.safe_load(expected_behavioral_config))


if __name__ == '__main__':
    unittest.main()
