"""Unit tests for Faucet State Collector"""

from unittest.mock import Mock, MagicMock
import unittest
from unittest.mock import patch
import os
import tempfile

import yaml

from unit_base import ForchestratorTestBase
from forch.authenticator import Authenticator
from forch.faucet_state_collector import FaucetStateCollector
from forch.faucetizer import Faucetizer
from forch.forchestrator import (Forchestrator, STATIC_BEHAVIORAL_FILE, STATIC_PLACEMENT_FILE,
                                 SEGMENTS_VLANS_FILE)
from forch.file_change_watcher import FileChangeWatcher
from forch.port_state_manager import PortStateManager
from forch.utils import dict_proto
from forch.proto.devices_state_pb2 import DevicePlacement, DeviceBehavior
from forch.proto.forch_configuration_pb2 import ForchConfig, OrchestrationConfig
from forch.proto.system_state_pb2 import SystemState


# pylint: disable=protected-access
class ForchestratorUnitTestCase(ForchestratorTestBase):
    """Test cases for dataplane state"""

    def test_faucet_config_validation(self):
        """Test validation for faucet config"""
        faucet_config_str = """
        dps:
          nz-kiwi-t1sw1:
            dp_id: 177
            faucet_dp_mac: 0e:00:00:00:01:01
            hardware: Generic
            lacp_timeout: 5
            stack:
              priority: 1
            interfaces:
              4:
                description: trunk
                tagged_vlans: [272]
              5:
                description: mirror
                tagged_vlans: [171]
              6:
                description: "to t1sw2 port 6"
                stack: {dp: nz-kiwi-t1sw2, port: 6}
              9:
                description: "to t2sw1 port 50"
                stack: {dp: nz-kiwi-t2sw1, port: 50}
              10:
                description: "to t2sw2 port 50"
                stack: {dp: nz-kiwi-t2sw2, port: 50}
              11:
                description: "to t2sw3 port 50"
                stack: {dp: nz-kiwi-t2sw3, port: 50}
              28:
                description: egress
                lacp: 3
                tagged_vlans: [171]
            lldp_beacon: {max_per_interval: 5, send_interval: 5}"""
        faucet_config = yaml.safe_load(faucet_config_str)
        self.assertEqual(self._forchestrator._validate_config(faucet_config),
                         [('nz-kiwi-t1sw1:04', 'misconfigured interface config: 0 0 0 0 0'),
                         ('nz-kiwi-t1sw1:05', 'misconfigured interface config: 0 0 0 0 0')])

    def test_config_error_detail(self):
        """Test config detail for config errors"""
        summaries = SystemState.SummarySources()
        self._forchestrator._faucet_events = Mock()
        self._forchestrator._get_controller_state = MagicMock(return_value=(2, 'test_detail'))
        self._forchestrator._forch_config_errors['static_behavior_file'] = 'File error'
        _, detail = self._forchestrator._get_combined_summary(summaries)
        self.assertTrue('forch' in detail)


# pylint: disable=protected-access
class ForchestratorAuthTestCase(ForchestratorTestBase):
    """Test case for forchestrator functionality with authenticator"""

    # pylint: disable=invalid-name
    def setUp(self):
        """setup fixture for each test method"""
        self._initialize_forchestrator()
        auth_config = dict_proto(
            {
                'radius_info': {
                    'server_ip': '0.0.0.0',
                    'server_port': 9999,
                    'source_port': 9999,
                    'radius_secret_helper':  f'{"echo radius_secret"}'
                }
            },
            OrchestrationConfig.AuthConfig
        )

        def handle_auth_result(src_mac, access, segment, role):
            device_behavior = DeviceBehavior(segment=segment, role=role)
            self._forchestrator._port_state_manager.handle_device_behavior(src_mac, device_behavior)

        self._forchestrator._authenticator = Authenticator(auth_config, handle_auth_result,
                                                           radius_query_object=Mock())
        sequester_config = OrchestrationConfig.SequesterConfig(sequester_segment='SEQUESTER')
        orch_config = OrchestrationConfig(sequester_config=sequester_config)
        self._forchestrator._port_state_manager = PortStateManager(
            Mock(), Mock(), orch_config=orch_config)

    def _get_auth_sm_state(self, mac):
        mac_sm = self._forchestrator._authenticator.sessions.get(mac)
        if mac_sm:
            return mac_sm.get_state()
        return None

    def test_auth_learn(self):
        """Test to validate MAC authentication status"""
        device_placement = DevicePlacement(switch='switch', port=1, connected=True)
        self._forchestrator._process_device_placement('00:11:22:33:44:55', device_placement)
        self.assertEqual(self._get_auth_sm_state('00:11:22:33:44:55'), 'RADIUS Request')
        self._forchestrator._authenticator.process_radius_result('00:11:22:33:44:55',
                                                                 'ACCEPT', 'ACCEPT', None)
        self.assertEqual(self._get_auth_sm_state('00:11:22:33:44:55'), 'Authorized')
        device_placement = DevicePlacement(switch='switch', port=1, connected=False)
        self._forchestrator._process_device_placement('00:11:22:33:44:55',
                                                      device_placement)
        self.assertEqual(self._get_auth_sm_state('00:11:22:33:44:55'), None)


# pylint: disable=protected-access
class ForchestratorMissingDVAFilesTestCase(unittest.TestCase):
    """Test case for forchestrator with missing DVA files."""
    _DEFAULT_FORCH_LOG = '/tmp/forch.log'

    FORCH_CONFIG = """
    orchestration:
      %s
      structural_config_file: faucet.yaml
      sequester_config:
        vlan_start: 272
        vlan_end: 276
        port_description: TAP
        auto_sequestering: disabled
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        os.environ['FORCH_LOG'] = self._DEFAULT_FORCH_LOG
        os.environ['FORCH_CONFIG_DIR'] = tempfile.mkdtemp()
        self._forchestrator = None

    @patch.object(Faucetizer, 'flush_behavioral_config', return_value=None)
    @patch.object(Faucetizer, 'tail_acl_config_valid', return_value=True)
    def setup(self, config, *args):
        """setup fixture for each test method"""
        forch_config = dict_proto(yaml.safe_load(config), ForchConfig)
        self._forchestrator = Forchestrator(forch_config)
        self._forchestrator._faucet_collector = FaucetStateCollector(
            self._forchestrator._config, is_faucetizer_enabled=True)
        self._forchestrator._should_enable_faucetizer = True
        with open(os.path.join(os.environ['FORCH_CONFIG_DIR'], 'faucet.yaml'), 'w') as fd:
            fd.write('segments_to_vlans:')
        self._forchestrator._config_file_watcher = FileChangeWatcher(
            os.environ['FORCH_CONFIG_DIR'])
        self._forchestrator._calculate_orchestration_config()
        self._forchestrator._initialize_orchestration()

    @patch.object(Faucetizer, 'reload_segments_to_vlans', return_value=None)
    def test_missing_static_device_behavior_file(self, *args):
        """Test a missing static_device_behavior file won't crash forch"""
        addon = """static_device_behavior: missing_file.yaml
      segments_vlans_file: segments_vlans.yaml"""
        self.setup(self.FORCH_CONFIG % addon)
        self.assertTrue(self._forchestrator._should_ignore_auth_result)
        self.assertIsNotNone(self._forchestrator._forch_config_errors.get(STATIC_BEHAVIORAL_FILE))

    def test_missing_static_device_placement_file(self):
        """Test a missing static_device_placement file won't crash forch"""
        addon = """static_device_placement: missing_file.yaml
      segments_vlans_file: missing_file.yaml"""
        self.setup(self.FORCH_CONFIG % addon)
        self.assertTrue(self._forchestrator._should_ignore_auth_result)
        self.assertIsNotNone(self._forchestrator._forch_config_errors.get(STATIC_PLACEMENT_FILE))

    def test_missing_segments_vlan_file(self):
        """Test a missing segments_vlan file won't crash forch"""
        addon = """segments_vlans_file: missing_file.yaml"""
        self.setup(self.FORCH_CONFIG % addon)
        self.assertTrue(self._forchestrator._should_ignore_auth_result)
        self.assertTrue(self._forchestrator._should_ignore_static_behavior)
        self.assertIsNotNone(self._forchestrator._forch_config_errors.get(SEGMENTS_VLANS_FILE))


if __name__ == '__main__':
    unittest.main()
