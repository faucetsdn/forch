"""Unit tests for Faucet State Collector"""

import unittest
from unit_base import FaucetStateCollectorTestBase

from forch.proto.faucet_event_pb2 import StackTopoChange
from forch.utils import dict_proto


class DataplaneStateTestCase(FaucetStateCollectorTestBase):
    """Test cases for dataplane state"""

    def _build_link(self, dp1, port1, dp2, port2):
        return {
            'key': dp1 + ':' + port1 + '-' + dp2 + ':' + port2,
            'source': dp1,
            'target': dp2,
            'port_map': {
                'dp_a': dp1,
                'port_a': 'Port ' + port1,
                'dp_z': dp2,
                'port_z': 'Port ' + port2
            }
        }

    def _build_loop_topo_obj(self):
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
        links_graph = [dict_proto(link, StackTopoChange.StackLink) for link in links]
        return {
            'dps': dps,
            'links_graph': links_graph
        }

    def _build_topo_obj(self):
        dps = {
            'sw1': StackTopoChange.StackDp(),
            'sw2': StackTopoChange.StackDp(root_hop_port=1),
            'sw3': StackTopoChange.StackDp(root_hop_port=1),
        }
        links = [
            self._build_link('sw1', '1', 'sw2', '1'),
            self._build_link('sw2', '2', 'sw3', '2'),
            self._build_link('sw3', '1', 'sw1', '2'),
        ]
        links_graph = [dict_proto(link, StackTopoChange.StackLink) for link in links]
        return {
            'active_root': 'sw1',
            'dps': dps,
            'links_graph': links_graph
        }

    def test_topology_loop(self):
        """test faucet_state_collector behavior when faucet sends loop in path to egress topology"""
        self._faucet_state_collector.topo_state = self._build_loop_topo_obj()
        egress_path = self._faucet_state_collector.get_switch_egress_path('sw1')
        self.assertEqual(egress_path['path_state'], 1)
        self.assertEqual(egress_path['path_state_detail'],
                         'No path to root found. Loop in topology.')

    def test_egress_path(self):
        """test faucet_state_collector behavior when faucet sends loop in path to egress topology"""
        self._faucet_state_collector.topo_state = self._build_topo_obj()
        # pylint: disable=protected-access
        self._faucet_state_collector._get_egress_port = lambda port: 28
        egress_path = self._faucet_state_collector.get_switch_egress_path('sw3')
        self.assertEqual(egress_path['path_state'], 5)
        self.assertEqual(egress_path['path'],
                         [{'switch': 'sw3', 'out': 1}, {'switch': 'sw1', 'in': 2, 'out': 28}])


if __name__ == '__main__':
    unittest.main()
