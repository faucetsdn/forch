"""Collecting the state of CPN components"""

import copy
from datetime import datetime
import logging
import os
import os.path
import re
import threading
import yaml

import forch.constants as constants
import forch.ping_manager

LOGGER = logging.getLogger('cpn')

KEY_NODES = 'cpn_nodes'
KEY_NODE_ATTRIBUTES = 'attributes'
KEY_NODE_PING_RES = 'ping_results'
KEY_NODE_STATUS = 'status'
KEY_NODE_STATUS_COUNT = 'status_count'
KEY_NODE_STATUS_UPDATE_TS = 'status_updated'
KEY_NODE_STATUS_CHANGE_TS = 'status_changed'

KEY_CPN_STATE = 'state'
KEY_CPN_STATE_COUNT = 'state_count'
KEY_CPN_STATE_UPDATE_TS = 'state_updated'
KEY_CPN_STATE_CHANGE_TS = 'state_changed'

PING_SUMMARY_REGEX = {'transmitted': r'\d+(?= packets transmitted)',
                      'received': r'\d+(?= received)',
                      'loss_percentage': r'\d+(?=% packet loss)',
                      'time_ms': r'(?<=time )\d+(?=ms)'}


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
                        node_state_map[KEY_NODE_ATTRIBUTES] = copy.copy(attr_map)
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
                cpn_node_map = cpn_nodes.setdefault(cpn_node, {})
                cpn_node_map['attributes'] = copy.copy(node_state.get(KEY_NODE_ATTRIBUTES, {}))
                cpn_node_map['status'] = node_state.get(KEY_NODE_STATUS, None)
                ping_result = node_state.get(KEY_NODE_PING_RES, {}).get('stdout', None)
                cpn_node_map['ping_results'] = CPNStateCollector._get_ping_summary(ping_result)
                cpn_node_map['status_change_count'] = node_state.get(KEY_NODE_STATUS_COUNT, None)
                cpn_node_map['status_last_updated'] = node_state.get(KEY_NODE_STATUS_UPDATE_TS, None)
                cpn_node_map['status_last_changed'] = node_state.get(KEY_NODE_STATUS_CHANGE_TS, None)

            return {
                'cpn_nodes': cpn_nodes,
                'cpn_state': self._cpn_state.get(KEY_CPN_STATE, None),
                'cpn_state_change_count': self._cpn_state.get(KEY_CPN_STATE_COUNT, None),
                'cpn_state_last_update': self._cpn_state.get(KEY_CPN_STATE_UPDATE_TS, None),
                'cpn_state_last_changed': self._cpn_state.get(KEY_CPN_STATE_CHANGE_TS, None)
            }

    def _handle_ping_result(self, ping_res_future):
        """Handle ping result for hosts"""
        ping_res_map = ping_res_future.result()
        current_time = datetime.now().isoformat()
        with self._lock:
            for host_name, res_map in ping_res_map.items():
                if host_name not in self._nodes_state:
                    continue
                node_state_map = self._nodes_state[host_name]

                last_status_count = node_state_map.get(KEY_NODE_STATUS_COUNT, 0)
                last_status = node_state_map.get(KEY_NODE_STATUS, None)
                new_status = CPNStateCollector._get_node_status(res_map)
                if not last_status or new_status != last_status:
                    node_state_map[KEY_NODE_STATUS] = new_status
                    node_state_map[KEY_NODE_STATUS_COUNT] = last_status_count + 1
                    node_state_map[KEY_NODE_STATUS_CHANGE_TS] = current_time

                node_state_map[KEY_NODE_STATUS_UPDATE_TS] = current_time
                node_state_map[KEY_NODE_PING_RES] = res_map

            self._update_cpn_state(current_time)

    @staticmethod
    def _get_node_status(ping_result):
        """Get node status from ping stdout"""
        result = re.search(r'\d+(?=% packet loss)', ping_result['stdout'])
        loss = int(result.group()) if result else 100
        if loss == 0:
            return constants.STATUS_HEALTHY
        if loss == 100:
            return constants.STATUS_DOWN
        return constants.STATUS_DAMAGED

    @staticmethod
    def _get_ping_summary(ping_stdout):
        """Get ping summary"""
        res_summary = {}
        if not ping_stdout:
            return None
        for line in ping_stdout.split('\n'):
            for summary_key, regex in PING_SUMMARY_REGEX.items():
                match = re.search(regex, line)
                if match:
                    res_summary[summary_key] = match.group()
            if 'rtt' == line[:3]:
                rtt_vals = re.findall(r'[0-9]*\.?[0-9]+', line)
                res_summary['rtt_ms'] = dict(zip(['min', 'avg', 'max', 'mdev'], rtt_vals))
        return res_summary

    def _update_cpn_state(self, current_time):
        new_cpn_state = self._get_cpn_status()
        if new_cpn_state != self._cpn_state.get(KEY_CPN_STATE, None):
            cpn_state_count = self._nodes_state.get(KEY_CPN_STATE_COUNT, 0) + 1
            self._cpn_state[KEY_CPN_STATE_COUNT] = cpn_state_count
            self._cpn_state[KEY_CPN_STATE_CHANGE_TS] = current_time
        self._cpn_state[KEY_CPN_STATE] = new_cpn_state
        self._cpn_state[KEY_CPN_STATE_UPDATE_TS] = current_time

    def _get_cpn_status(self):
        n_healthy = 0
        for node, node_state in self._nodes_state.items():
            if node_state.get(KEY_NODE_STATUS, "") == constants.STATUS_HEALTHY:
                n_healthy += 1
        if n_healthy == len(self._nodes_state):
            return constants.STATUS_HEALTHY
        if n_healthy == 0:
            return constants.STATUS_DOWN
        return constants.STATUS_DAMAGED
