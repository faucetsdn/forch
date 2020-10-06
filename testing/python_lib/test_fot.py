"""Integration test base class for Forch"""

import threading
import time
import unittest
import yaml

from forch.utils import dict_proto, proto_dict

from forch.proto.devices_state_pb2 import DeviceBehavior, DevicesState
from forch.proto.shared_constants_pb2 import Empty

from integration_base import IntegrationTestBase
from unit_base import (
    DeviceReportServerTestBase, FaucetizerTestBase, PortsStateManagerTestBase
)


class FotConfigTest(IntegrationTestBase):
    """Test suite for dynamic config changes"""

    def test_stack_connectivity(self):
        """Test to build stack and check for connectivity"""
        print('Running test_stack_connectivity')
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


class FotDeviceReportServerTestCase(DeviceReportServerTestBase):
    """Device testing server test case"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = threading.Lock()
        self._received_device_events = []

    def _process_devices_state(self, devices_state):
        devices_state_map = proto_dict(devices_state, including_default_value_fields=True)
        with self._lock:
            for mac, device_behavior in devices_state_map['device_mac_behaviors'].items():
                self._received_device_events.append((mac, device_behavior['device_event']))

    def _encapsulate_mac_device_event(self, mac, device_event):
        devices_state_map = {
            'device_mac_behaviors': {
                mac: {'device_event': device_event}
            }
        }
        return dict_proto(devices_state_map, DevicesState)

    def test_receiving_devices_states(self):
        """Test behavior of the behavior when client sends device testing states"""
        expected_mac_device_events = [
            ('00:0X:00:00:00:01', 'unknown'),
            ('00:0Y:00:00:00:02', 'passed'),
            ('00:0Z:00:00:00:03', 'cleared'),
            ('00:0A:00:00:00:04', 'passed'),
            ('00:0B:00:00:00:05', 'unknown')
        ]

        future_responses = []
        for mac_device_event in expected_mac_device_events:
            print(f'Sending devices state: {mac_device_event}')
            future_response = self._client.ReportDevicesState.future(
                self._encapsulate_mac_device_event(*mac_device_event))
            future_responses.append(future_response)

        for future_response in future_responses:
            self.assertEqual(type(future_response.result()), Empty)

        sorted_received_states = sorted(self._received_device_events)
        sorted_expected_states = sorted(expected_mac_device_events)

        self.assertEqual(sorted_received_states, sorted_expected_states)


class FotPortStatesTestCase(PortsStateManagerTestBase):
    """Test access port testing states"""

    def _process_device_behavior(self, mac, device_behavior, static=False):
        print(f'Received device behavior for device {mac}: {device_behavior}, {static}')
        self._received_device_behaviors.append((mac, device_behavior.segment, static))

    def _encapsulate_testing_result(self, mac, device_event):
        devices_state_map = {
            'device_mac_behaviors': {
                mac: {'device_event': device_event}
            }
        }
        return dict_proto(devices_state_map, DevicesState)

    def test_ports_states(self):
        """Test the testing states with different signals"""
        static_device_behaviors = {
            '00:0X:00:00:00:01': {'segment': 'SEG_A', 'device_event': 'cleared'},
            '00:0Y:00:00:00:02': {'device_event': 'cleared'}
        }
        authentication_results = {
            '00:0X:00:00:00:01': {'segment': 'SEG_X'},
            '00:0Z:00:00:00:03': {'segment': 'SEG_C'},
            '00:0A:00:00:00:04': {'segment': 'SEG_D'}
        }
        testing_results = [
            ('00:0X:00:00:00:01', 'failed'),
            ('00:0Y:00:00:00:02', 'passed'),
            ('00:0Z:00:00:00:03', 'failed'),
            ('00:0A:00:00:00:04', 'passed')
        ]
        unauthenticated_devices = ['00:0X:00:00:00:01', '00:0A:00:00:00:04']

        # load static device behaviors
        for mac, device_behavior_map in static_device_behaviors.items():
            self._port_state_manager.handle_static_device_behavior(
                mac, dict_proto(device_behavior_map, DeviceBehavior))

        # devices are authenticated
        for mac, device_behavior_map in authentication_results.items():
            self._port_state_manager.handle_device_behavior(
                mac, dict_proto(device_behavior_map, DeviceBehavior))

        expected_states = {
            '00:0X:00:00:00:01': self.OPERATIONAL,
            '00:0Z:00:00:00:03': self.SEQUESTERED,
            '00:0A:00:00:00:04': self.SEQUESTERED
        }
        self._verify_ports_states(expected_states)

        expected_received_device_behaviors = [
            ('00:0X:00:00:00:01', 'SEG_A', True),
            ('00:0X:00:00:00:01', 'SEG_A', True),
            ('00:0Z:00:00:00:03', 'TESTING', False),
            ('00:0A:00:00:00:04', 'TESTING', False)
        ]
        self._verify_received_device_behaviors(expected_received_device_behaviors)

        # received testing results for devices
        for testing_result in testing_results:
            self._port_state_manager.handle_testing_result(
                self._encapsulate_testing_result(*testing_result))

        expected_states = {
            '00:0X:00:00:00:01': self.OPERATIONAL,
            '00:0Z:00:00:00:03': self.INFRACTED,
            '00:0A:00:00:00:04': self.OPERATIONAL
        }
        self._verify_ports_states(expected_states)

        expected_received_device_behaviors.extend([('00:0A:00:00:00:04', 'SEG_D', False)])
        self._verify_received_device_behaviors(expected_received_device_behaviors)

        # devices are unauthenticated
        for mac in unauthenticated_devices:
            self._port_state_manager.handle_device_behavior(mac, DeviceBehavior())

        expected_states = {
            '00:0X:00:00:00:01': self.OPERATIONAL,
            '00:0Z:00:00:00:03': self.INFRACTED
        }
        self._verify_ports_states(expected_states)

        expected_received_device_behaviors.extend([('00:0A:00:00:00:04', '', False)])
        self._verify_received_device_behaviors(expected_received_device_behaviors)


if __name__ == '__main__':
    unittest.main()
