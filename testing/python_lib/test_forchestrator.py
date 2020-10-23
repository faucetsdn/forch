"""Unit tests for Faucet State Collector"""

from unittest.mock import Mock
import unittest
import yaml
from unit_base import ForchestratorTestBase
from forch.authenticator import Authenticator
from forch.port_state_manager import PortStateManager
from forch.utils import dict_proto, proto_dict
from forch.proto.devices_state_pb2 import DevicePlacement, DeviceBehavior
from forch.proto.forch_configuration_pb2 import OrchestrationConfig
from forch.proto.faucet_configuration_pb2 import Interface, StackLink, Datapath, Vlan, FaucetConfig, LLDPBeacon, Stack


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
        # self.assertFalse(self._forchestrator._validate_config(faucet_config))
        config = proto_dict(self._create_scale_faucet_config(2, 3, 10))
        print(config)
        with open('/tmp/yaml_dump.yaml', 'w') as config_file:
            yaml.dump(config, config_file)
        return

    def _build_t1_interfaces(self, dp_index, t1_dps, t2_dps, t2_port, tagged_vlans, tap_vlan=None):
        interfaces = {}
        if tap_vlan:
            interfaces[4] = Interface(description='tap', tagged_vlans=[tap_vlan])
        for index, dp in enumerate(t1_dps):
            if abs(dp_index - index) == 1:
                port = 6 + min(dp_index, index)
                description = ("to %s port %s" % (dp, port))
                interfaces[port] = Interface(description=description, stack=StackLink(dp=dp, port=port))
        for index, dp in enumerate(t2_dps):
            port = 100 + index
            description = ("to %s port %s" % (dp, t2_port))
            interfaces[port] = Interface(description=description, stack=StackLink(dp=dp, port=t2_port))
        interfaces[28] = Interface(description='egress', lacp=3, tagged_vlans=tagged_vlans)
        return interfaces

    def _build_t2_interfaces(self, dp_index, t1_dps, access_ports, native_vlan, port_acl):
        interfaces = {}
        for index in range(access_ports):
            interfaces[index + 101] = Interface(description='IoT Device', native_vlan=native_vlan, acl_in=port_acl, max_hosts=1)
        for index, dp in enumerate(t1_dps):
            port = 50 + index * 2
            description = ('to %s port %s' % (dp, 100+dp_index))
            interfaces[port] = Interface(description=description, stack=StackLink(dp=dp, port=100+dp_index))
        return interfaces

    def _build_datapath_config(self, dp_id, mac, interfaces):
        lldp_beacon = LLDPBeacon(max_per_interval=5, send_interval=5)
        stack = Stack(priority=1)
        return Datapath(dp_id=dp_id, faucet_dp_mac=mac, hardware='Generic', lacp_timeout=5, lldp_beacon=lldp_beacon, interfaces=interfaces, stack=stack)

    def _create_scale_faucet_config(self, t1_switches, t2_switches, access_ports):
        setup_vlan = 171
        test_vlan = 272
        vlans = {
            str(setup_vlan): Vlan(description='Faucet IoT'),
            str(test_vlan): Vlan(description='Orchestrated Testing')
        }
        t1_dps = [('nz-kiwi-t1sw%s' % (dp_index + 1)) for dp_index in range(t1_switches)]
        t2_dps = [('nz-kiwi-t2sw%s' % (dp_index + 1)) for dp_index in range(t2_switches)]
        dps = {}
        for dp_index, dp_name in enumerate(t1_dps):
            tap_vlan = test_vlan if not dp_index else None
            interfaces = self._build_t1_interfaces(dp_index, t1_dps, t2_dps, 50 + dp_index * 2, [setup_vlan], tap_vlan)
            print(interfaces)
            dps[dp_name] = self._build_datapath_config(177 + dp_index, ('0e:00:00:00:01:%s' % ("{:02x}".format(dp_index+1))), interfaces)

        for dp_index, dp_name in enumerate(t2_dps):
            interfaces = self._build_t2_interfaces(dp_index, t1_dps, access_ports, setup_vlan, 'uniform_acl')
            print(interfaces)
            dps[dp_name] = self._build_datapath_config(1295 + dp_index, ('0e:00:00:00:02:%s' % ("{:02x}".format(dp_index+1))), interfaces)

        return FaucetConfig(dps=dps, version=2, include=['uniform.yaml'], vlans=vlans)


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

        def get_vlan_from_segment(segment):
            if segment == 'ACCEPT':
                return 100
            return 999

        self._forchestrator._authenticator = Authenticator(auth_config, handle_auth_result,
                                                           radius_query_object=Mock())
        self._forchestrator._port_state_manager = PortStateManager(
            Mock(), Mock(), get_vlan_from_segment, 'SEQUESTER')

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
                                                      device_placement, expired_vlan=200)
        self.assertEqual(self._get_auth_sm_state('00:11:22:33:44:55'), 'Authorized')
        self._forchestrator._process_device_placement('00:11:22:33:44:55',
                                                      device_placement, expired_vlan=100)
        self.assertEqual(self._get_auth_sm_state('00:11:22:33:44:55'), None)


if __name__ == '__main__':
    unittest.main()
