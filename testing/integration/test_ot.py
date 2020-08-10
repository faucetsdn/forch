"""Integration test base class for Forch"""
import unittest
import time

from forch.faucetizer import Faucetizer
from forch.utils import dict_proto

from forch.proto.devices_state_pb2 import DevicePlacement, DeviceBehavior
from forch.proto.forch_configuration_pb2 import OrchestrationConfig

from testing.test_lib.integration_base import IntegrationTestBase, logger


class OTConfigTest(IntegrationTestBase):
    """Test suite for dynamic config changes"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def test_stack_connectivity(self):
        """Test to build stack and check for connectivity"""
        logger.debug('Running test_stack_connectivity')
        self._clean_stack()
        self._setup_stack()
        self.assertTrue(self._ping_host('forch-faux-1', '192.168.1.2'))
        self.assertFalse(self._ping_host('forch-faux-1', '192.168.1.12'))
        self._clean_stack()

    def test_ot_sequester(self):
        """Test to check if OT trunk sequesters traffic as expected"""
        self._clean_stack()
        self._setup_stack()
        self.assertTrue(self._ping_host('forch-faux-1', '192.168.1.2'))

        self._generate_sequestering_config()
        time.sleep(5)

        self.assertTrue(self._ping_host('forch-faux-1', '192.168.2.1'))
        self.assertFalse(self._ping_host('forch-faux-1', '192.168.1.2'))
        self._clean_stack()

    def _generate_sequestering_config(self):
        orch_config_map = {
            'fot_config': {
                'testing_segment': 'TESTING',
                'testing_vlan_start': 1000,
                'testing_vlan_end': 1999,
                'testing_port_identifier': 'trunk'
            }
        }
        orch_config = dict_proto(orch_config_map, OrchestrationConfig)
        structural_config_file = self._get_faucet_config_path()
        behivoral_config_file = self._get_faucet_config_path()
        segments_to_vlans = {'HOST': 272}

        faucetizer = Faucetizer(
            orch_config, structural_config_file, segments_to_vlans, behivoral_config_file)
        faucetizer.reload_structural_config()

        mac = '0A:00:00:00:00:01'
        device_placement_map = {
            'switch': 'nz-kiwi-t2sw1',
            'port': 1,
            'connected': True
        }
        device_behavior_map = {
            'segment': 'TESTING'
        }
        device_placement = dict_proto(device_placement_map, DevicePlacement)
        device_behavior = dict_proto(device_behavior_map, DeviceBehavior)

        faucetizer.process_device_placement(mac, device_placement)
        faucetizer.process_device_behavior(mac, device_behavior)


if __name__ == '__main__':
    unittest.main()
