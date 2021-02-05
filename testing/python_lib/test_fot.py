"""Integration test base class for Forch"""

import re
import threading
import time
import unittest
import yaml
import grpc

from integration_base import IntegrationTestBase

from unit_base import (
    DeviceReportServerTestBase, DeviceReportServicerTestBase, FaucetizerTestBase,
    PortsStateManagerTestBase
)

from forch.utils import dict_proto, proto_dict

from forch.proto.devices_state_pb2 import (
    DeviceBehavior, DevicePlacement,
    DevicesState, Device, DevicePortEvent
)
from forch.proto.shared_constants_pb2 import Empty, PortBehavior
from forch.proto.grpc.device_report_pb2 import DESCRIPTOR


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


def encapsulate_mac_port_behavior(mac, port_behavior):
    """Converts to proto object for mac port behavior"""
    devices_state_map = {
        'device_mac_behaviors': {
            mac: {'port_behavior': port_behavior}
        }
    }
    return dict_proto(devices_state_map, DevicesState)

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

    def test_receiving_devices_states(self):
        """Test behavior of the server when client sends devices states"""
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
                encapsulate_mac_port_behavior(*mac_port_behavior))
            future_responses.append(future_response)

        for future_response in future_responses:
            self.assertEqual(type(future_response.result()), Empty)

        sorted_received_behaviors = sorted(self._received_mac_port_behaviors)
        sorted_expected_behaviors = sorted(expected_mac_port_behaviors)

        self.assertEqual(sorted_received_behaviors, sorted_expected_behaviors)


class FotDeviceReportServicerTestCase(DeviceReportServicerTestBase):
    """Device report servicer test case (With mock grpc services)"""

    def test_requesting_empty_port_events(self):
        """Test behavior of the servicer with no port events."""

        method = self._setup_port_state_server('00:0X:00:00:00:01')

        mac_port_behavior = encapsulate_mac_port_behavior('00:0X:00:00:00:01', 'passed')
        print(f'Sending devices state: {mac_port_behavior}')
        self._test_server.invoke_unary_unary(
            DESCRIPTOR.services_by_name['DeviceReport'].methods_by_name['ReportDevicesState'],
            invocation_metadata={},
            request=mac_port_behavior, timeout=1
        )

        _, code, _ = method.termination()
        self.assertEqual(code, grpc.StatusCode.OK)

    def _setup_port_state_server(self, mac_addr):
        device = Device(mac=mac_addr)
        return self._test_server.invoke_unary_stream(
            DESCRIPTOR.services_by_name['DeviceReport'].methods_by_name['GetPortState'],
            invocation_metadata={},
            request=device, timeout=1
        )

    def _send_port_change_event(self, kind, args):
        dp_name, port, mac, state, vlan, assigned = args
        if kind == 'port':
            self._servicer.process_port_change(dp_name, port, state)
        elif kind == 'lern':
            self._servicer.process_port_learn(dp_name, port, mac, vlan)
        elif kind == 'asgn':
            self._servicer.process_port_assign(mac, assigned)

    def _check_port_change_event(self, response, expected):
        _, _, _, state, vlan, assigned = expected
        state = PortBehavior.PortState.up if state else PortBehavior.PortState.down
        self.assertEqual(response.state, state)
        self.assertEqual(response.device_vlan, vlan)
        self.assertEqual(response.assigned_vlan, assigned)

    def test_requesting_port_events(self):
        """Test behavior of the servicer with port events."""

        mac_addr = "00:0X:00:00:00:01"
        method = self._setup_port_state_server(mac_addr)

        port_changes = [
            ('port', ('name', '1', mac_addr, False, 0, 0)),
            ('lern', ('name', '1',  mac_addr, True, 102, 0)),
            ('asgn', ('name', '1',  mac_addr, True, 102, 103)),
            ('port', ('name', '1', mac_addr, True, 102, 103)),
            ('port', ('name', '2', None, True, 103, 0)),
            ('port', ('name', '5', None, False, 103, 0)),
            ('port', ('name', '1', mac_addr, False, 0, 0)),
            ('port', ('name', '1', mac_addr, True, 0, 0)),
        ]
        for port_change in port_changes:
            self._send_port_change_event(port_change[0], port_change[1])

        # For some reason this is required to cause the streaming RPC to terminate cleanly.
        self._report_device_state()

        expected_port_changes = filter(lambda changes: changes[1][1] == '1', port_changes)
        count = 0
        for expected in expected_port_changes:
            response = method.take_response()
            self.assertEqual(type(response), DevicePortEvent)
            self._check_port_change_event(response, expected[1])
            count += 1
        self.assertEqual(count, 6)

        _, code, _ = method.termination()
        self.assertEqual(code, grpc.StatusCode.OK)

    def _report_device_state(self):
        """Test updating device state"""
        mac_addr = "00:0X:00:00:00:01"
        mac_port_behavior = encapsulate_mac_port_behavior(mac_addr, 'passed')
        print(f'Sending devices state: {mac_port_behavior}')
        method = self._test_server.invoke_unary_unary(
            DESCRIPTOR.services_by_name['DeviceReport'].methods_by_name['ReportDevicesState'],
            invocation_metadata={},
            request=mac_port_behavior, timeout=1
        )
        _, _, code, _ = method.termination()
        self.assertEqual(code, grpc.StatusCode.OK)


class FotPortStatesTestCase(PortsStateManagerTestBase):
    """Test access port states"""

    def _process_device_placement(self, mac, device_placement, static=False):
        print(f'Received device placement for device {mac}: {device_placement}, {static}')
        self._received_device_placements.append((mac, device_placement.connected, static))

    def _process_device_behavior(self, mac, device_behavior, static=False):
        print(f'Received device behavior for device {mac}: {device_behavior}, {static}')
        self._received_device_behaviors.append((mac, device_behavior.segment, static))

    def _get_vlan_from_segment(self, segment):
        segments_to_vlans = {
            'SEG_A': 100, 'SEG_B': 200, 'SEG_C': 300, 'SEG_D': 400, 'SEG_E': 500, 'SEG_X': 600,
        }
        return segments_to_vlans.get(segment)

    def _encapsulate_testing_result(self, mac, port_behavior):
        devices_state_map = {
            'device_mac_behaviors': {
                mac: {'port_behavior': port_behavior}
            }
        }
        return dict_proto(devices_state_map, DevicesState)

    def test_ports_states(self):
        """Test the port states with different signals"""
        static_device_placements = {
            '00:0Y:00:00:00:02': {'switch': 't2sw2', 'port': 1, 'connected': True},
            '00:0Z:00:00:00:03': {'switch': 't2sw3', 'port': 1, 'connected': True}
        }
        dynamic_device_placements = {
            '00:0X:00:00:00:01': {'switch': 't2sw1', 'port': 1, 'connected': True},
            '00:0A:00:00:00:04': {'switch': 't2sw4', 'port': 4, 'connected': True},
            '00:0B:00:00:00:05': {'switch': 't2sw5', 'port': 5, 'connected': True}
        }
        static_device_behaviors = {
            '00:0X:00:00:00:01': {'segment': 'SEG_A', 'port_behavior': 'cleared'},
            '00:0Y:00:00:00:02': {'port_behavior': 'cleared'}
        }
        authentication_results = {
            '00:0X:00:00:00:01': {'segment': 'SEG_X'},
            '00:0Z:00:00:00:03': {'segment': 'SEG_C'},
            '00:0A:00:00:00:04': {'segment': 'SEG_D'},
            '00:0B:00:00:00:05': {'segment': 'SEG_E'}
        }
        testing_results = [
            ('00:0X:00:00:00:01', 'failed'),
            ('00:0Y:00:00:00:02', 'passed'),
            ('00:0Z:00:00:00:03', 'failed'),
            ('00:0A:00:00:00:04', 'passed')
        ]
        expired_device_placements = [
            ('00:0X:00:00:00:01', ('t2sw1', 1)),
            ('00:0B:00:00:00:05', ('t2sw5', 5)),
            ('00:0B:00:00:00:05', ('t2sw5', 5)),
        ]
        unauthenticated_devices = ['00:0X:00:00:00:01', '00:0A:00:00:00:04']
        reauthenticated_device = {'00:0A:00:00:00:04': {'segment': 'SEG_D'}}

        expected_device_placements = []
        expected_device_behaviors = []

        # load static device placements
        self._load_static_device_placements(static_device_placements, expected_device_placements)

        # load static device behaviors
        self._load_static_device_behaviors(static_device_behaviors)

        # devices are learned
        self._learn_devices(dynamic_device_placements, expected_device_placements)

        # devices are authenticated
        self._authenticate_devices(authentication_results, expected_device_behaviors)

        # received testing results for devices
        self._receive_testing_results(testing_results, expected_device_behaviors)

        # devices are expired
        self._expire_devices(expired_device_placements, expected_device_placements)

        # devices are unauthenticated
        self._unauthenticate_devices(unauthenticated_devices, expected_device_behaviors)

        # devices are reauthenticated
        self._reauthenticate_devices(reauthenticated_device, expected_device_behaviors)

    def _load_static_device_placements(self, static_device_placements, expected_device_placements):
        for mac, device_placement_map in static_device_placements.items():
            self._port_state_manager.handle_device_placement(mac, dict_proto(
                device_placement_map, DevicePlacement), static=True)

        expected_device_placements.extend([
            # mac, connected, static
            ('00:0Y:00:00:00:02', True, True),
            ('00:0Z:00:00:00:03', True, True),
        ])
        self._verify_received_device_placements(expected_device_placements)

    def _load_static_device_behaviors(self, static_device_behaviors):
        for mac, device_behavior_map in static_device_behaviors.items():
            self._port_state_manager.handle_static_device_behavior(
                mac, dict_proto(device_behavior_map, DeviceBehavior))

        expected_states = {
            '00:0Y:00:00:00:02': self.UNAUTHENTICATED,
            '00:0Z:00:00:00:03': self.UNAUTHENTICATED
        }
        self._verify_ports_states(expected_states)

    def _learn_devices(self, dynamic_device_placements, expected_device_placements):
        for mac, device_placement_map in dynamic_device_placements.items():
            self._port_state_manager.handle_device_placement(mac, dict_proto(
                device_placement_map, DevicePlacement), static=False)

        expected_device_placements.extend([
            ('00:0X:00:00:00:01', True, False),
            ('00:0A:00:00:00:04', True, False),
            ('00:0B:00:00:00:05', True, False)
        ])
        self._verify_received_device_placements(expected_device_placements)

    def _authenticate_devices(self, authentication_results, expected_device_behaviors):
        for mac, device_behavior_map in authentication_results.items():
            self._port_state_manager.handle_device_behavior(
                mac, dict_proto(device_behavior_map, DeviceBehavior))

        expected_states = {
            '00:0X:00:00:00:01': self.OPERATIONAL,
            '00:0Y:00:00:00:02': self.UNAUTHENTICATED,
            '00:0Z:00:00:00:03': self.SEQUESTERED,
            '00:0A:00:00:00:04': self.SEQUESTERED,
            '00:0B:00:00:00:05': self.SEQUESTERED
        }
        self._verify_ports_states(expected_states)

        expected_device_behaviors.extend([
            ('00:0X:00:00:00:01', 'SEG_A', True),
            ('00:0X:00:00:00:01', 'SEG_A', True),
            ('00:0Z:00:00:00:03', 'TESTING', False),
            ('00:0A:00:00:00:04', 'TESTING', False),
            ('00:0B:00:00:00:05', 'TESTING', False)
        ])
        self._verify_received_device_behaviors(expected_device_behaviors)

    def _receive_testing_results(self, testing_results, expected_device_behaviors):
        for testing_result in testing_results:
            self._port_state_manager.handle_testing_result(
                self._encapsulate_testing_result(*testing_result))

        expected_states = {
            '00:0X:00:00:00:01': self.OPERATIONAL,
            '00:0Y:00:00:00:02': self.UNAUTHENTICATED,
            '00:0Z:00:00:00:03': self.INFRACTED,
            '00:0A:00:00:00:04': self.OPERATIONAL,
            '00:0B:00:00:00:05': self.SEQUESTERED
        }
        self._verify_ports_states(expected_states)

        expected_device_behaviors.extend([
            ('00:0Z:00:00:00:03', '', False),
            ('00:0A:00:00:00:04', 'SEG_D', False)
        ])
        self._verify_received_device_behaviors(expected_device_behaviors)

    def _expire_devices(self, expired_device_placements, expected_device_placements):
        for expired_device_placement in expired_device_placements:
            mac = None
            switch = expired_device_placement[1][0]
            port = expired_device_placement[1][1]
            self._port_state_manager.handle_device_placement(
                mac, DevicePlacement(switch=switch, port=port), False)

        expected_device_placements.extend([
            # mac, device_placement.connected, static
            ('00:0X:00:00:00:01', False, False),
            ('00:0B:00:00:00:05', False, False)
        ])
        self._verify_received_device_placements(expected_device_placements)

    def _unauthenticate_devices(self, unauthenticated_devices, expected_device_behaviors):
        for mac in unauthenticated_devices:
            self._port_state_manager.handle_device_behavior(mac, DeviceBehavior())

        expected_states = {
            '00:0Y:00:00:00:02': self.UNAUTHENTICATED,
            '00:0Z:00:00:00:03': self.INFRACTED,
            '00:0A:00:00:00:04': self.UNAUTHENTICATED
        }
        self._verify_ports_states(expected_states)

        expected_device_behaviors.extend([('00:0A:00:00:00:04', '', False)])
        self._verify_received_device_behaviors(expected_device_behaviors)

    def _reauthenticate_devices(self, reauthenticated_device, expected_device_behaviors):
        for mac, device_behavior_map in reauthenticated_device.items():
            self._port_state_manager.handle_device_behavior(
                mac, dict_proto(device_behavior_map, DeviceBehavior))

        expected_states = {
            '00:0Y:00:00:00:02': self.UNAUTHENTICATED,
            '00:0Z:00:00:00:03': self.INFRACTED,
            '00:0A:00:00:00:04': self.SEQUESTERED
        }
        self._verify_ports_states(expected_states)

        expected_device_behaviors.extend([('00:0A:00:00:00:04', 'TESTING', False)])
        self._verify_received_device_behaviors(expected_device_behaviors)


class FotSequesterTest(IntegrationTestBase):
    """Base class for sequestering integration tests"""

    def _sequester_device(self):
        config = self._read_faucet_config()
        interface = config['dps']['nz-kiwi-t2sw1']['interfaces'][1]
        interface['native_vlan'] = 272
        self._write_faucet_config(config)
        time.sleep(5)


class FotConfigTest(FotSequesterTest):
    """Simple config change tests for fot"""

    def test_fot_sequester(self):
        """Test to check if OT trunk sequesters traffic as expected"""
        self.assertTrue(self._ping_host('forch-faux-1', '192.168.1.2'))
        self.assertFalse(self._ping_host('forch-faux-1', '192.168.2.1'))

        self._sequester_device()

        self.assertFalse(self._ping_host('forch-faux-1', '192.168.1.2'))
        self.assertTrue(self._ping_host('forch-faux-1', '192.168.2.1'))


class FotContainerTest(IntegrationTestBase):
    """Test suite for dynamic config changes"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stack_options['static_switch'] = True
        self.stack_options['fot'] = True

    def _internal_dhcp(self, device_container):
        def dhclient_method(container=None):
            def run_dhclient():
                try:
                    self._run_cmd('dhclient -r', docker_container=container)
                    self._run_cmd('timeout 20s dhclient', docker_container=container)
                except Exception as e:
                    print(e)
            return run_dhclient

        device_tcpdump_text = self.tcpdump_helper(
            'faux-eth0', 'port 67 or port 68', packets=10,
            funcs=[dhclient_method(container=device_container)],
            timeout=10, docker_host=device_container)
        vlan_tcpdump_text = self.tcpdump_helper(
            'data0', 'vlan 272 and port 67', packets=10,
            funcs=[dhclient_method(container=device_container)],
            timeout=10, docker_host='forch-controller-1')
        return device_tcpdump_text, vlan_tcpdump_text

    def test_dhcp_reflection(self):
        """Test to check DHCP reflection when on test VLAN"""
        # trigger learning event for faux-1 to make it authenticated and sequestered
        self._run_cmd('ping -c1 -w2 8.8.8.8', docker_container='forch-faux-1', strict=False)

        # test DHCP reflection with sequestered device
        device_tcpdump_text, vlan_tcpdump_text = self._internal_dhcp('forch-faux-1')
        self.assertTrue(re.search("DHCP.*Reply", device_tcpdump_text))
        self.assertTrue(re.search("DHCP.*Reply", vlan_tcpdump_text))

        # test DHCP with unauthenticated device
        device_tcpdump_text, vlan_tcpdump_text = self._internal_dhcp('forch-faux-3')
        self.assertFalse(re.search("DHCP.*Reply", device_tcpdump_text))
        self.assertFalse(re.search("DHCP.*Reply", vlan_tcpdump_text))


if __name__ == '__main__':
    unittest.main()
