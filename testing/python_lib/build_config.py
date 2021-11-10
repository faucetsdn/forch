"""Generates faucet config for given number of switches and number of devices per switch"""

import getopt
import sys
import yaml
from forch.utils import proto_dict
from forch.proto.faucet_configuration_pb2 import Interface, StackLink, Datapath, \
    Vlan, FaucetConfig, LLDPBeacon, Stack

CORP_DP_ID = 273
T1_DP_ID_START = 177
T2_DP_ID_START = 1295
FLAT_DP_ID_START = 513
SETUP_VLAN = 171
TEST_VLAN = 272
FLAT_LINK_PORT_START = 6
T1_STACK_PORT_START = 100
T2_STACK_PORT_START = 50
DEFAULT_ACCESS_PORT_START = 101
FLAT_ACCESS_PORT_START = 1
TAP_PORT = 4
FAUCET_EGRESS_PORT = 28
FLAT_EGRESS_PORT = 50
CORP_EGRESS_PORT = 10
LACP_MODE = 3
T1_DP_MAC_PREFIX = '0e:00:00:00:01:'
T2_DP_MAC_PREFIX = '0e:00:00:00:02:'
FLAT = 'flat'
CORP = 'corp'
STACK = 'stack'
T1_DP = 't1'
T2_DP = 't2'


# pylint: disable=protected-access
# pylint: disable=too-many-arguments
class FaucetConfigGenerator():
    """Class for generating faucet config for given switches and devices per switch"""

    def _build_dp_interfaces(self, dp_index, **kwargs):
        interfaces = {}

        # add egress interface
        egress_port = kwargs.get('egress_port')
        tagged_vlans = kwargs.get('tagged_vlans')
        lacp = kwargs.get('lacp')
        if egress_port:
            self._add_egress_interface(interfaces, egress_port, tagged_vlans, lacp)

        # add tap interface
        tap_vlan = kwargs.get('tap_vlan')
        if tap_vlan:
            self._add_tap_interface(interfaces, tap_vlan)

        # add flat link interfaces
        dps = kwargs.get('dps')
        if dps:
            self._add_flat_link_interfaces(interfaces, dps, dp_index)

        # add stack interfaces linking from t1 to t2 switches
        t2_dps = kwargs.get('t2_dps')
        if t2_dps:
            self._add_t1_stack_interfaces(interfaces, dp_index, t2_dps)

        # add stack interfaces linking from t2 to t1 switches
        t1_dps = kwargs.get('t1_dps')
        if t1_dps:
            self._add_t2_stack_interfaces(interfaces, dp_index, t1_dps)

        # add access interfaces
        access_ports = kwargs.get('access_ports')
        access_port_start = kwargs.get('access_port_start', DEFAULT_ACCESS_PORT_START)
        native_vlan = kwargs.get('native_vlan')
        port_acl = kwargs.get('port_acl')
        if access_ports:
            self._add_access_interfaces(
                interfaces, access_ports, access_port_start, native_vlan, port_acl)

        return interfaces

    def _add_egress_interface(self, interfaces, egress_port, tagged_vlans, lacp):
        if lacp:
            interfaces[egress_port] = Interface(
                description='egress', lacp=LACP_MODE, tagged_vlans=tagged_vlans)
        else:
            interfaces[egress_port] = Interface(
                description='egress', tagged_vlans=tagged_vlans)

    def _add_tap_interface(self, interfaces, tap_vlan):
        interfaces[TAP_PORT] = Interface(description='TAP', tagged_vlans=[tap_vlan])

    def _add_flat_link_interfaces(self, interfaces, dps, dp_index):
        if dp_index < len(dps) - 1:
            next_dp = dps[dp_index + 1]
            next_port = FLAT_LINK_PORT_START + dp_index
            description = ("to %s port %s" % (next_dp, next_port))
            interfaces[next_port] = Interface(
                description=description, stack=StackLink(dp=next_dp, port=next_port))

        if dp_index > 0:
            prev_dp = dps[dp_index - 1]
            prev_port = FLAT_LINK_PORT_START + (len(dps) + dp_index - 1) % len(dps)
            description = ("to %s port %s" % (prev_dp, prev_port))
            interfaces[prev_port] = Interface(
                description=description, stack=StackLink(dp=prev_dp, port=prev_port))

    def _add_t1_stack_interfaces(self, interfaces, dp_index, t2_dps):
        t2_port = T2_STACK_PORT_START + dp_index * 2
        for index, t2_dp in enumerate(t2_dps):
            port = T1_STACK_PORT_START + index
            description = ("to %s port %s" % (t2_dp, t2_port))
            interfaces[port] = Interface(
                description=description, stack=StackLink(dp=t2_dp, port=t2_port))

    def _add_t2_stack_interfaces(self, interfaces, dp_index, t1_dps):
        t1_port = T1_STACK_PORT_START + dp_index
        for index, t1_dp in enumerate(t1_dps):
            port = T2_STACK_PORT_START + index * 2
            description = ('to %s port %s' % (t1_dp, t1_port))
            interfaces[port] = Interface(
                description=description, stack=StackLink(dp=t1_dp, port=t1_port))

    def _add_access_interfaces(self, interfaces, access_ports, access_port_start, native_vlan,
                               port_acl):
        for index in range(access_ports):
            interfaces[index + access_port_start] = Interface(
                description='IoT Device', native_vlan=native_vlan, acl_in=port_acl,
                max_hosts=1)

    def _build_datapath_config(self, dp_id, interfaces, mac=None):
        lldp_beacon = LLDPBeacon(max_per_interval=5, send_interval=5)
        stack = Stack(priority=1)
        return Datapath(
            dp_id=dp_id, faucet_dp_mac=mac, hardware='Generic',
            lacp_timeout=5, lldp_beacon=lldp_beacon, interfaces=interfaces, stack=stack)

    def _generate_dp_mac(self, dp_type, dp_index):
        if dp_type == T1_DP:
            return T1_DP_MAC_PREFIX + "{:02x}".format(dp_index+1)

        if dp_type == T2_DP:
            return T2_DP_MAC_PREFIX + "{:02x}".format(dp_index+1)

        raise Exception('Unknown dp_type: %s' % dp_type)

    def create_scale_faucet_config(self, t1_switches, t2_switches, access_ports):
        """Create Faucet config with stacking topology"""
        setup_vlan = SETUP_VLAN
        test_vlan = TEST_VLAN
        vlans = {
            setup_vlan: Vlan(description='Faucet IoT'),
            test_vlan: Vlan(description='Orchestrated Testing')
        }
        t1_dps = [('nz-kiwi-t1sw%s' % (dp_index + 1)) for dp_index in range(t1_switches)]
        t2_dps = [('nz-kiwi-t2sw%s' % (dp_index + 1)) for dp_index in range(t2_switches)]
        dps = {}
        for dp_index, dp_name in enumerate(t1_dps):
            tap_vlan = test_vlan if not dp_index else None
            interfaces = self._build_dp_interfaces(
                dp_index, dps=t1_dps, t2_dps=t2_dps, tagged_vlans=[setup_vlan],
                tap_vlan=tap_vlan, egress_port=FAUCET_EGRESS_PORT, lacp=True)
            dps[dp_name] = self._build_datapath_config(
                T1_DP_ID_START + dp_index, interfaces, self._generate_dp_mac(T1_DP, dp_index))

        for dp_index, dp_name in enumerate(t2_dps):
            interfaces = self._build_dp_interfaces(
                dp_index, t1_dps=t1_dps, access_ports=access_ports, native_vlan=setup_vlan,
                port_acl='uniform_acl', lacp=True)
            dps[dp_name] = self._build_datapath_config(
                T2_DP_ID_START + dp_index, interfaces, self._generate_dp_mac(T2_DP, dp_index))
        return FaucetConfig(dps=dps, version=2, include=['uniform.yaml'], vlans=vlans)

    def create_flat_faucet_config(self, num_switches, num_access_ports):
        """Create Faucet config with flat topology"""
        setup_vlan = SETUP_VLAN
        switches = [('sw%s' % (sw_num + 1)) for sw_num in range(num_switches)]
        dps = {}
        vlans = {setup_vlan: Vlan(description='Faucet IoT')}

        for sw_num, sw_name in enumerate(switches):
            interfaces = self._build_dp_interfaces(
                sw_num, dps=switches, egress_port=FAUCET_EGRESS_PORT, tagged_vlans=[setup_vlan],
                access_ports=num_access_ports, native_vlan=setup_vlan, port_acl='uniform_acl',
                access_port_start=FLAT_ACCESS_PORT_START, lacp=True)
            dps[sw_name] = self._build_datapath_config(
                FLAT_DP_ID_START + sw_num, interfaces, self._generate_dp_mac(T2_DP, sw_num))

        return FaucetConfig(dps=dps, version=2, include=['uniform.yaml'], vlans=vlans)

    def create_corp_faucet_config(self):
        """Create Faucet config for corp network"""
        setup_vlan = SETUP_VLAN
        switch = 'corp'
        dps = {}

        interfaces = self._build_dp_interfaces(
            CORP_DP_ID, tagged_vlans=[setup_vlan], access_ports=1, access_port_start=1,
            native_vlan=setup_vlan, egress_port=CORP_EGRESS_PORT)
        dps[switch] = self._build_datapath_config(CORP_DP_ID, interfaces)
        return FaucetConfig(dps=dps, version=2)


def cleanup_interfaces(config_map):
    """proto_dict converstaion converts int keys to strings, which causes problems with faucet."""
    interfaces = config_map['dps']['corp']['interfaces']
    int_interfaces = {}
    for interface in interfaces:
        int_interfaces[int(interface)] = interfaces[interface]
    config_map['dps']['corp']['interfaces'] = int_interfaces
    return config_map


def main(argv):
    """main method for standalone run"""
    config_generator = FaucetConfigGenerator()
    filepath = '/tmp/faucet_config_dump'
    egress = 2
    access = 3
    devices = 1
    topo_type = STACK
    argv = argv[1:]

    help_msg = """
    <python3> build_config.py -e <egress_switches> -a <access_switches> -d <devices per switch>
    -p <config path> -t <topology type (flat, corp, stack)>
    """

    try:
        opts, _ = getopt.getopt(
            argv, 'he:a:d:p:t:', ['egress=', 'access=', 'devices=', 'path=', 'type='])
    except getopt.GetoptError:
        print(help_msg)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(help_msg)
            sys.exit()
        elif opt in ('-e', '--egress'):
            egress = int(arg)
        elif opt in ('-a', '--access'):
            access = int(arg)
        elif opt in ('-d', '--devices'):
            devices = int(arg)
        elif opt in ('-p', '--path'):
            filepath = arg
        elif opt in ('-t', '--type'):
            topo_type = arg

    if topo_type == FLAT:
        faucet_config = config_generator.create_flat_faucet_config(access, devices)
    elif topo_type == CORP:
        faucet_config = config_generator.create_corp_faucet_config()
    elif topo_type == STACK:
        faucet_config = config_generator.create_scale_faucet_config(egress, access, devices)
    else:
        raise Exception('Unkown topology type: %s' % topo_type)

    config_map = cleanup_interfaces(proto_dict(faucet_config))

    with open(filepath, 'w') as config_file:
        yaml.dump(config_map, config_file)


if __name__ == '__main__':
    main(sys.argv)
