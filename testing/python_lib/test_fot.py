"""Integration test base class for Forch"""

import threading
import time
import unittest
import yaml

from forch.utils import dict_proto, proto_dict

from forch.proto.grpc.device_testing_pb2 import DeviceTestingState
from forch.proto.shared_constants_pb2 import TestingState, Empty

from integration_base import IntegrationTestBase, logger
from unit_base import DeviceTestingServerTestBase, FaucetizerTestBase


class FotConfigTest(IntegrationTestBase):
    """Test suite for dynamic config changes"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def test_stack_connectivity(self):
        """Test to build stack and check for connectivity"""
        logger.debug('Running test_stack_connectivity')
        self.assertTrue(self._ping_host('forch-faux-1', '192.168.1.2'))
        self.assertFalse(self._ping_host('forch-faux-1', '192.168.1.12'))

    def test_fot_sequester(self):
        """Test to check if OT trunk sequesters traffic as expected"""
        self.assertTrue(self._ping_host('forch-faux-1', '192.168.1.2'))

        config = self._read_faucet_config()
        interface = config['dps']['nz-kiwi-t2sw1']['interfaces'][1]
        interface['native_vlan'] = 272
        self._write_faucet_config(config)
        time.sleep(5)
        self.assertTrue(self._ping_host('forch-faux-1', '192.168.2.1'))
        self.assertFalse(self._ping_host('forch-faux-1', '192.168.1.2'))


class FotFaucetizerTestCase(FaucetizerTestBase):
    """Faucetizer test"""

    FORCH_CONFIG = """
    orchestration:
      unauthenticated_vlan: 100
      fot_config:
        testing_segment: TESTING
        testing_vlan_start: 1500
        testing_vlan_end: 1699
        testing_port_identifier: TESTING
    """

    def test_device_states(self):
        """test Faucet behavioral config generation at different devices states"""

        placements = [
            # mocking static placements
            ('02:0A:00:00:00:01', {'switch': 't2sw1', 'port': 1, 'connected': True}, True),
            # devices dynamically learned
            ('02:0b:00:00:00:02', {'switch': 't2sw2', 'port': 1, 'connected': True}, False),
        ]

        behaviors = [
            # mocking static behaviors
            ('02:0a:00:00:00:01', {'segment': 'SEG_A', 'role': 'red'}, True),
            # devices to be sequestered
            ('02:0a:00:00:00:01', {'segment': 'TESTING'}, False),
            ('02:0B:00:00:00:02', {'segment': 'TESTING'}, False),
            # devices to be operational
            ('02:0B:00:00:00:02', {'segment': 'SEG_B'}, False),
        ]

        # process static device info
        self._process_device_placement(placements[0])
        self._process_device_behavior(behaviors[0])

        # devices are learned and sent to sequestering
        self._process_device_placement(placements[1])
        self._process_device_behavior(behaviors[1])
        self._process_device_behavior(behaviors[2])

        expected_config = yaml.safe_load(self.FAUCET_BEHAVIORAL_CONFIG)
        self._update_port_config(
            expected_config, switch='t2sw1', port=1, native_vlan=200, role='red')
        self._update_port_config(expected_config, switch='t2sw2', port=1, native_vlan=1501)
        self._update_port_config(expected_config, switch='t1sw1', port=4, tagged_vlans=[272, 1501])

        # devices allowed to be operational
        self._process_device_behavior(behaviors[3])

        expected_config = yaml.safe_load(self.FAUCET_BEHAVIORAL_CONFIG)
        self._update_port_config(
            expected_config, switch='t2sw1', port=1, native_vlan=200, role='red')
        self._update_port_config(expected_config, switch='t2sw2', port=1, native_vlan=300)


class FotDeviceTestingServerTestCase(DeviceTestingServerTestBase):
    """Device testing server test case"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = threading.Lock()
        self._received_states = []

    def _process_device_testing_state(self, device_testing_state):
        with self._lock:
            self._received_states.append(
                proto_dict(device_testing_state, including_default_value_fields=True))

    def test_receiving_device_testing_states(self):
        """Test behavior of the behavior when client sends device testing states"""
        expected_testing_states = [
            {'mac': '00:0X:00:00:00:01', 'testing_state': 'unknown'},
            {'mac': '00:0Y:00:00:00:02', 'testing_state': 'passed'},
            {'mac': '00:0Z:00:00:00:03', 'testing_state': 'testing'},
            {'mac': '00:0A:00:00:00:04', 'testing_state': 'testing'},
            {'mac': '00:0B:00:00:00:05', 'testing_state': 'unknown'}
        ]

        future_responses = []
        for testing_state in expected_testing_states:
            logger.info('Sending device testing state: %s', testing_state)
            future_response = self._client.ReportTestingState.future(
                dict_proto(testing_state, DeviceTestingState))
            future_responses.append(future_response)

        for future_response in future_responses:
            self.assertEqual(type(future_response.result()), Empty)

        print(self._received_states) # TODO remove
        print(expected_testing_states)  # TODO remove

        sorted_received_states = sorted(self._received_states, key=lambda k: k['mac'])
        sorted_expected_states = sorted(expected_testing_states, key=lambda k: k['mac'])

        self.assertEqual(sorted_received_states, sorted_expected_states)


if __name__ == '__main__':
    unittest.main()
