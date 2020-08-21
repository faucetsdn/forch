"""Unit tests for Faucet State Collector"""

import unittest
from unit_base import FaucetStateCollectorTestBase

from forch.faucet_state_collector import FaucetStateCollector
from forch.proto.forch_configuration_pb2 import OrchestrationConfig
from forch.proto.devices_state_pb2 import DevicePlacement, DeviceBehavior
from forch.proto.faucet_event_pb2 import StackTopoChange
from forch.utils import dict_proto, str_proto


class DataplaneStateTestCase(FaucetStateCollectorTestBase):
    """Test cases for dataplane state"""

    def _build_link(self, dp1, port1, dp2, port2):
        return {
            'key': dp1 +':'+ port1 +'-'+ dp2 +':'+ port2,
            'source': dp1,
            'target': dp2,
            'port_map': {
                'dp_a': dp1,
                'port_a': 'Port ' + port1,
                'dp_z': dp2,
                'port_z': 'Port ' + port2
            }
        }

    def _build_topo_obj(self):
        dps = {
            'sw1': StackTopoChange.StackDp(root_hop_port=1),
            'sw2': StackTopoChange.StackDp(root_hop_port=1),
            'sw3': StackTopoChange.StackDp(root_hop_port=1),
        }
        links = [
            self._build_link('sw1', '1', 'sw2', '2'),
            self._build_link('sw2', '1', 'sw3', '2'),
            self._build_link('sw3', '1', 'sw1', '2'),
        ]
        links_graph = [ dict_proto(link, StackTopoChange.StackLink) for link in links ]
        return {
            'dps': dps,
            'links_graph': links_graph
        }

    def test_topology_loop(self):
        """test faucet_state_collector behavior when faucet sends loop in path to egress topology"""
        self._faucet_state_collector.topo_state = self._build_topo_obj()
        egress_path = self._faucet_state_collector.get_switch_egress_path('sw1')
        self.assertEqual(egress_path['path_state'], 1)
        self.assertEqual(egress_path['path_state_detail'], 'No path to root found. Loop in topology.')


if __name__ == '__main__':
    unittest.main()
