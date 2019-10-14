"""Collecting the state of CPN components"""

import copy
from datetime import datetime
import logging
import os
import os.path
import re
import threading
import yaml

import forch.ping_manager

LOGGER = logging.getLogger('cpn')

KEY_NODES = 'cpn_nodes'
KEY_CPN_ATTRIBUTES = 'attributes'
KEY_CPN_PING_RES = 'ping_results'
KEY_CPN_STATUS = 'status'
KEY_CPN_STATUS_COUNT = 'status_count'
KEY_CPN_STATUS_TS = 'status_updated'


class CPNStateCollector:
    """Processing and storing CPN components states"""
    def __init__(self):
        self._cpn_state = {}
        self._nodes_state = self._cpn_state.setdefault(KEY_NODES, {})
        self._hosts_ip = {}
        self._lock = threading.Lock()
        self._ping_manager = None

        cpn_dir_name = os.getenv('FORCH_CONFIG_DIR')
        cpn_file_name = os.path.join(cpn_dir_name, 'cpn.yaml')
        if cpn_file_name:
            LOGGER.info("Loading CPN config file: %s", cpn_file_name)
            try:
                with open(cpn_file_name) as cpn_file:
                    cpn_data = yaml.safe_load(cpn_file)
                    cpn_nodes = cpn_data.get('cpn_nodes', {})

                    for node, attr_map in cpn_nodes.items():
                        node_state_map = self._nodes_state.setdefault(node, {})
                        node_state_map[KEY_CPN_ATTRIBUTES] = copy.copy(attr_map)
                        self._hosts_ip[node] = attr_map['cpn_ip']

                    self._ping_manager = forch.ping_manager.PingManager(self._hosts_ip)

            except OSError as e:
                LOGGER.warning(e)
        else:
            LOGGER.warning("CPN Config file is not specified")

        if self._ping_manager:
            self._ping_manager.start_loop(self._handle_ping_result)

    def get_cpn_summary(self):
        """Get summary of cpn info"""
        return {
            'state': 'broken',
            'detail': 'not implemented',
            'change_count': 1
        }

    def get_cpn_state(self):
        """Get CPN state"""
        cpn_nodes = {}

        with self._lock:
            for cpn_node, node_state in self._nodes_state.items():
                ret_node_map = cpn_nodes.setdefault(cpn_node, {})
                ret_node_map['attributes'] = copy.copy(node_state.get(KEY_CPN_ATTRIBUTES, {}))
                ret_node_map['status'] = node_state.get(KEY_CPN_STATUS, None)
                ping_result = node_state.get(KEY_CPN_PING_RES, {}).get('stdout', None)
                ret_node_map['ping_results'] = CPNStateCollector._get_ping_summary(ping_result)
                ret_node_map['status_change_count'] = node_state.get(KEY_CPN_STATUS_COUNT, None)
                ret_node_map['status_last_updated'] = node_state.get(KEY_CPN_STATUS_TS, None)

        return {
            'cpn_state': 'monkey',
            'cpn_state_change_count': 1,
            'cpn_state_last_update': "2019-10-11T15:23:21.382479",
            'cpn_state_last_changed': "2019-10-11T15:23:21.382479",
            'cpn_nodes': cpn_nodes
        }

    def _handle_ping_result(self, ping_res_future):
        """Handle ping result for hosts"""
        ping_res_map = ping_res_future.result()
        with self._lock:
            for host_name, res_map in ping_res_map.items():
                if host_name not in self._nodes_state:
                    continue
                node_state_map = self._nodes_state[host_name]

                last_status_count = node_state_map.get(KEY_CPN_STATUS_COUNT, 0)
                last_status = node_state_map.get(KEY_CPN_STATUS, None)
                new_status = CPNStateCollector._get_node_status(res_map)
                if not last_status or new_status != last_status:
                    node_state_map[KEY_CPN_STATUS] = new_status
                    node_state_map[KEY_CPN_STATUS_COUNT] = last_status_count + 1
                    node_state_map[KEY_CPN_STATUS_TS] = datetime.now().isoformat()

                node_state_map[KEY_CPN_PING_RES] = res_map

    @staticmethod
    def _get_node_status(ping_result):
        """Get node status from ping stdout"""
        result = re.search(r'\d+(?=% packet loss)', ping_result['stdout'])
        loss = int(result.group()) if result else 100
        if loss == 0:
            return 'healthy'
        if loss == 100:
            return 'down'
        return 'flaky'

    @staticmethod
    def _get_ping_summary(ping_stdout):
        """Get ping summary"""
        if not ping_stdout:
            return None
        reach_stats = False
        stats_lines = []
        for line in ping_stdout.split('\n'):
            if reach_stats:
                stats_lines.append(line)
            if not reach_stats and 'ping statistics' in line:
                reach_stats = True
        return '\n'.join(stats_lines)
