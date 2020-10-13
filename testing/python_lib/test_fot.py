"""Integration test base class for Forch"""

import re
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
      sequester_config:
        segment: TESTING
        vlan_start: 1500
        vlan_end: 1699
        port_description: TESTING
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
    """Device report server test case"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = threading.Lock()
        self._received_mac_port_behaviors = []

    def _process_devices_state(self, devices_state):
        devices_state_map = proto_dict(devices_state, including_default_value_fields=True)
        with self._lock:
            for mac, device_behavior in devices_state_map['device_mac_behaviors'].items():
                self._received_mac_port_behaviors.append((mac, device_behavior['port_behavior']))

    def _encapsulate_mac_port_behavior(self, mac, port_behavior):
        devices_state_map = {
            'device_mac_behaviors': {
                mac: {'port_behavior': port_behavior}
            }
        }
        return dict_proto(devices_state_map, DevicesState)

    def test_receiving_devices_states(self):
        """Test behavior of the behavior when client sends devices states"""
        expected_mac_port_behaviors = [
            ('00:0X:00:00:00:01', 'unknown'),
            ('00:0Y:00:00:00:02', 'passed'),
            ('00:0Z:00:00:00:03', 'cleared'),
            ('00:0A:00:00:00:04', 'passed'),
            ('00:0B:00:00:00:05', 'unknown')
        ]

        future_responses = []
        for mac_port_behavior in expected_mac_port_behaviors:
            print(f'Sending devices state: {mac_port_behavior}')
            future_response = self._client.ReportDevicesState.future(
                self._encapsulate_mac_port_behavior(*mac_port_behavior))
            future_responses.append(future_response)

        for future_response in future_responses:
            self.assertEqual(type(future_response.result()), Empty)

        sorted_received_behaviors = sorted(self._received_mac_port_behaviors)
        sorted_expected_behaviors = sorted(expected_mac_port_behaviors)

        self.assertEqual(sorted_received_behaviors, sorted_expected_behaviors)


class FotPortStatesTestCase(PortsStateManagerTestBase):
    """Test access port states"""

    def _process_device_behavior(self, mac, device_behavior, static=False):
        print(f'Received device behavior for device {mac}: {device_behavior}, {static}')
        self._received_device_behaviors.append((mac, device_behavior.segment, static))

    def _encapsulate_testing_result(self, mac, port_behavior):
        devices_state_map = {
            'device_mac_behaviors': {
                mac: {'port_behavior': port_behavior}
            }
        }
        return dict_proto(devices_state_map, DevicesState)

    def test_ports_states(self):
        """Test the port states with different signals"""
        static_device_behaviors = {
            '00:0X:00:00:00:01': {'segment': 'SEG_A', 'port_behavior': 'cleared'},
            '00:0Y:00:00:00:02': {'port_behavior': 'cleared'}
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


class FotContainerTest(IntegrationTestBase):
    """Test suite for dynamic config changes"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stack_options['fot'] = True
        self.stack_options['local'] = True

    def test_dhcp_reflection(self):
        """Test to check DHCP reflection when on test VLAN"""
        def dhclient_method(container=None):
            def run_dhclient():
                try:
                    self._run_cmd('dhclient -r', docker_container=container)
                    self._run_cmd('dhclient', docker_container=container)
                except Exception as e:
                    print(e)
            return run_dhclient
        config = self._read_faucet_config()
        tcpdump_text = self.tcpdump_helper('faux-eth0', 'port 67 or port 68', packets=10,
                                           funcs=[dhclient_method(container='forch-faux-1')],
                                           timeout=10, docker_host='forch-faux-1')
        self.assertTrue(re.search("DHCP.*Reply", tcpdump_text))
        interface = config['dps']['nz-kiwi-t2sw1']['interfaces'][1]
        interface['native_vlan'] = 272
        self._write_faucet_config(config)
        time.sleep(5)
        tcpdump_text = self.tcpdump_helper('faux-eth0', 'port 67 or port 68', packets=10,
                                           funcs=[dhclient_method(container='forch-faux-1')],
                                           timeout=10, docker_host='forch-faux-1')
        self.assertTrue(re.search("DHCP.*Reply", tcpdump_text))

if __name__ == '__main__':
    unittest.main()
