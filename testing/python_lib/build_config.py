"""Generates faucet config for given number of switches and number of devices per switch"""

import getopt
import sys
import yaml
from forch.utils import proto_dict
from forch.proto.faucet_configuration_pb2 import Interface, StackLink, Datapath, \
    Vlan, FaucetConfig, LLDPBeacon, Stack


# pylint: disable=protected-access
# pylint: disable=too-many-arguments
class FaucetConfigGenerator():
    """Class for generating faucet config for given switches and devices per switch"""

    def _build_t1_interfaces(self, dp_index, t1_dps, t2_dps, t2_port, tagged_vlans, tap_vlan=None):
        interfaces = {}
        if tap_vlan:
            interfaces[4] = Interface(description='tap', tagged_vlans=[tap_vlan])
        for index, dp_name in enumerate(t1_dps):
            if abs(dp_index - index) == 1:
                port = 6 + min(dp_index, index)
                description = ("to %s port %s" % (dp_name, port))
                interfaces[port] = Interface(description=description,
                                             stack=StackLink(dp=dp_name, port=port))
        for index, dp_name in enumerate(t2_dps):
            port = 100 + index
            description = ("to %s port %s" % (dp_name, t2_port))
            interfaces[port] = Interface(description=description,
                                         stack=StackLink(dp=dp_name, port=t2_port))
        interfaces[28] = Interface(description='egress', lacp=3, tagged_vlans=tagged_vlans)
        return interfaces

    def _build_t2_interfaces(self, dp_index, t1_dps, access_ports, native_vlan, port_acl):
        interfaces = {}
        for index in range(access_ports):
            interfaces[index + 101] = Interface(description='IoT Device',
                                                native_vlan=native_vlan, acl_in=port_acl,
                                                max_hosts=1)
        for index, dp_name in enumerate(t1_dps):
            port = 50 + index * 2
            description = ('to %s port %s' % (dp_name, 100+dp_index))
            interfaces[port] = Interface(description=description,
                                         stack=StackLink(dp=dp_name, port=100+dp_index))
        return interfaces

    def _build_datapath_config(self, dp_id, mac, interfaces):
        lldp_beacon = LLDPBeacon(max_per_interval=5, send_interval=5)
        stack = Stack(priority=1)
        return Datapath(dp_id=dp_id, faucet_dp_mac=mac, hardware='Generic',
                        lacp_timeout=5, lldp_beacon=lldp_beacon, interfaces=interfaces, stack=stack)

    def _create_scale_faucet_config(self, t1_switches, t2_switches, access_ports):
        setup_vlan = 171
        test_vlan = 272
        vlans = {
            setup_vlan: Vlan(description='Faucet IoT'),
            test_vlan: Vlan(description='Orchestrated Testing')
        }
        t1_dps = [('nz-kiwi-t1sw%s' % (dp_index + 1)) for dp_index in range(t1_switches)]
        t2_dps = [('nz-kiwi-t2sw%s' % (dp_index + 1)) for dp_index in range(t2_switches)]
        dps = {}
        for dp_index, dp_name in enumerate(t1_dps):
            tap_vlan = test_vlan if not dp_index else None
            interfaces = self._build_t1_interfaces(dp_index, t1_dps, t2_dps,
                                                   50 + dp_index * 2, [setup_vlan], tap_vlan)
            dps[dp_name] = self._build_datapath_config(
                177 + dp_index, ('0e:00:00:00:01:%s' % ("{:02x}".format(dp_index+1))), interfaces)

        for dp_index, dp_name in enumerate(t2_dps):
            interfaces = self._build_t2_interfaces(dp_index,
                                                   t1_dps, access_ports, setup_vlan, 'uniform_acl')
            dps[dp_name] = self._build_datapath_config(
                1295 + dp_index, ('0e:00:00:00:02:%s' % ("{:02x}".format(dp_index+1))), interfaces)
        return FaucetConfig(dps=dps, version=2, include=['uniform.yaml'], vlans=vlans)


def main(argv):
    """main method for standalone run"""
    config_generator = FaucetConfigGenerator()
    filepath = '/tmp/faucet_config_dump'
    egress = 2
    access = 3
    devices = 1
    argv = argv[1:]
    try:
        opts, _ = getopt.getopt(argv, 'he:a:d:p:', ['egress=', 'access=', 'devices=', 'path='])
    except getopt.GetoptError:
        print('<python3> build_config.py -e <egress_switches> -a'
              '<access_switches> -d <devices per switch> -p <config path>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('<python3> build_config.py -e <egress_switches> -a '
                  '<access_switches> -d <devices per switch> -p <config path>')
            sys.exit()
        elif opt in ('-e', '--egress'):
            egress = int(arg)
        elif opt in ('-a', '--access'):
            access = int(arg)
        elif opt in ('-d', '--devices'):
            devices = int(arg)
        elif opt in ('-p', '--path'):
            filepath = arg
    config = proto_dict(config_generator._create_scale_faucet_config(egress, access, devices))
    with open(filepath, 'w') as config_file:
        yaml.dump(config, config_file)


if __name__ == '__main__':
    main(sys.argv)
