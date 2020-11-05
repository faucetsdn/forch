"""Collecting the state of CPN components"""

from datetime import datetime
import os
import os.path
import re
import threading

from forch.ping_manager import PingManager
from forch.utils import dict_proto, get_logger, proto_dict, yaml_proto

from forch.proto.cpn_config_pb2 import CpnConfig
from forch.proto.cpn_state_pb2 import CpnState
from forch.proto.shared_constants_pb2 import State
from forch.proto.system_state_pb2 import StateSummary

LOGGER = get_logger('cstate')

NODE_ATTRIBUTES = 'attributes'
NODE_PING_RES = 'ping_results'
NODE_STATE = 'state'
NODE_STATE_CHANGE_COUNT = 'state_change_count'
NODE_STATE_UPDATE_TS = 'state_update'
NODE_STATE_CHANGE_TS = 'state_change'
PING_STATE = 'ping_state'
PING_STATE_CONSECUTIVE_COUNT = 'ping_state_consecutive_count'

CPN_STATE = 'state'
CPN_STATE_DETAIL = 'detail'
CPN_STATE_COUNT = 'state_count'
CPN_STATE_UPDATE_TS = 'state_update'
CPN_STATE_CHANGE_TS = 'state_change'

MIN_CONSECUTIVE_PING_HEALTHY_DEFAULT = 3
MIN_CONSECUTIVE_PING_DOWN_DEFAULT = 5
PING_INTERVAL_DEFAULT = 2

PING_SUMMARY_REGEX = {'transmitted': r'\d+(?= packets transmitted)',
                      'received': r'\d+(?= received)',
                      'loss_percentage': r'\d+(?=% packet loss)',
                      'time_ms': r'(?<=time )\d+(?=ms)'}


class CPNStateCollector:
    """Processing and storing CPN components states"""
    def __init__(self, config):
        self._cpn_state = {}
        self._node_states = {}
        self._hosts_ip = {}
        self._min_consecutive_healthy = (
            config.min_consecutive_ping_healthy or MIN_CONSECUTIVE_PING_HEALTHY_DEFAULT)
        self._min_consecutive_down = (
            config.min_consecutive_ping_down or MIN_CONSECUTIVE_PING_DOWN_DEFAULT)
        self.ping_interval = config.ping_interval or PING_INTERVAL_DEFAULT
        self._lock = threading.Lock()
        self._ping_manager = None

    def initialize(self):
        """Initialize this instance and make it go"""
        cpn_dir_name = os.getenv('FORCH_CONFIG_DIR')
        cpn_file_name = os.path.join(cpn_dir_name, 'cpn.yaml')
        current_time = datetime.now().isoformat()
        LOGGER.info("Loading CPN config file: %s", cpn_file_name)
        try:
            cpn_data = yaml_proto(cpn_file_name, CpnConfig)
            cpn_nodes = cpn_data.cpn_nodes

            for node, attr_map in cpn_nodes.items():
                node_state_map = self._node_states.setdefault(node, {})
                node_state_map[NODE_ATTRIBUTES] = attr_map
                self._hosts_ip[node] = attr_map.cpn_ip

            if not self._hosts_ip:
                raise Exception('No CPN components defined in file')

            self._ping_manager = PingManager(self._hosts_ip, self.ping_interval)
            self._update_cpn_state(current_time, State.initializing, "Initializing")
        except Exception as e:
            LOGGER.error('Could not load config file: %s', e)
            self._node_states.clear()
            self._update_cpn_state(current_time, State.broken, str(e))

        if self._ping_manager:
            self._ping_manager.start_loop(self._handle_ping_result)

    def get_cpn_summary(self):
        """Get summary of cpn info"""
        return dict_proto({
            'state': self._cpn_state.get(CPN_STATE),
            'detail': self._cpn_state.get(CPN_STATE_DETAIL),
            'change_count': self._cpn_state.get(CPN_STATE_COUNT),
            'last_update': self._cpn_state.get(CPN_STATE_UPDATE_TS),
            'last_change': self._cpn_state.get(CPN_STATE_CHANGE_TS)
        }, StateSummary)

    def get_cpn_state(self):
        """Get CPN state"""
        cpn_nodes = {}

        with self._lock:
            for cpn_node, node_state in self._node_states.items():
                cpn_node_map = cpn_nodes.setdefault(cpn_node, {})
                cpn_node_map['attributes'] = proto_dict(node_state.get(NODE_ATTRIBUTES))
                cpn_node_map['state'] = node_state.get(NODE_STATE)
                ping_result = node_state.get(NODE_PING_RES, {}).get('stdout')
                cpn_node_map['ping_results'] = CPNStateCollector._get_ping_summary(ping_result)
                cpn_node_map['state_change_count'] = node_state.get(NODE_STATE_CHANGE_COUNT)
                cpn_node_map['state_last_update'] = node_state.get(NODE_STATE_UPDATE_TS)
                cpn_node_map['state_last_change'] = node_state.get(NODE_STATE_CHANGE_TS)

            return dict_proto({
                'cpn_nodes': cpn_nodes,
                'cpn_state': self._cpn_state.get(CPN_STATE),
                'cpn_state_detail': self._cpn_state.get(CPN_STATE_DETAIL),
                'cpn_state_change_count': self._cpn_state.get(CPN_STATE_COUNT),
                'cpn_state_last_update': self._cpn_state.get(CPN_STATE_UPDATE_TS),
                'cpn_state_last_change': self._cpn_state.get(CPN_STATE_CHANGE_TS)
            }, CpnState)

    def _handle_ping_result(self, ping_res_future):
        """Handle ping result for hosts"""
        ping_res_map = ping_res_future.result()
        current_time = datetime.now().isoformat()
        with self._lock:
            for host_name, res_map in ping_res_map.items():
                if host_name not in self._node_states:
                    continue

                node_state_map = self._node_states[host_name]
                last_state = node_state_map.get(NODE_STATE)
                new_state = self._get_node_state(node_state_map, res_map)

                if not last_state or new_state != last_state:
                    state_count = node_state_map.get(NODE_STATE_CHANGE_COUNT, 0) + 1
                    LOGGER.info('cpn_state #%d host %s is %s', state_count, host_name, new_state)
                    node_state_map[NODE_STATE] = new_state
                    node_state_map[NODE_STATE_CHANGE_COUNT] = state_count
                    node_state_map[NODE_STATE_CHANGE_TS] = current_time

                node_state_map[NODE_STATE_UPDATE_TS] = current_time
                node_state_map[NODE_PING_RES] = res_map

            self._update_cpn_state(current_time)

    @staticmethod
    def _get_ping_state(ping_result):
        """Get node state from ping stdout"""
        result = re.search(r'\d+(?=% packet loss)', ping_result['stdout'])
        loss = int(result.group()) if result else 100
        if loss == 0:
            return State.healthy

        return State.down

    def _get_node_state(self, node_state_map, ping_result):
        last_ping_state = node_state_map.get(PING_STATE)
        new_ping_state = self._get_ping_state(ping_result)
        node_state_map[PING_STATE] = new_ping_state

        last_consecutive_count = node_state_map.get(PING_STATE_CONSECUTIVE_COUNT, 0)
        new_consecutive_count = (last_consecutive_count + 1 if new_ping_state == last_ping_state
                                 else 0)
        node_state_map[PING_STATE_CONSECUTIVE_COUNT] = new_consecutive_count

        if (new_ping_state == State.healthy and
                new_consecutive_count >= self._min_consecutive_healthy):
            return State.healthy

        if (new_ping_state == State.down and
                new_consecutive_count >= self._min_consecutive_down):
            return State.down

        return State.damaged

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
            if line[:3] == 'rtt':
                rtt_vals = re.findall(r'[0-9]*\.?[0-9]+', line)
                res_summary['rtt_ms'] = dict(zip(['min', 'avg', 'max', 'mdev'], rtt_vals))
        return res_summary

    def _update_cpn_state(self, current_time, state=None, detail=None):
        new_cpn_state, broken = (state, None) if state else self._get_cpn_state()

        if detail:
            use_detail = detail
        elif broken:
            use_detail = 'CPN failures at: ' + ', '.join(broken)
        else:
            use_detail = ''

        if new_cpn_state != self._cpn_state.get(CPN_STATE):
            cpn_state_count = self._cpn_state.get(CPN_STATE_COUNT, 0) + 1
            self._cpn_state[CPN_STATE_COUNT] = cpn_state_count
            self._cpn_state[CPN_STATE] = new_cpn_state
            self._cpn_state[CPN_STATE_CHANGE_TS] = current_time
            LOGGER.info('cpn_state #%d %s: %s', cpn_state_count, new_cpn_state, use_detail)
        self._cpn_state[CPN_STATE_DETAIL] = use_detail
        self._cpn_state[CPN_STATE_UPDATE_TS] = current_time

    def _get_cpn_state(self):
        broken = []
        if not self._node_states:
            return State.broken, broken
        for node_name, node_state in self._node_states.items():
            if node_state.get(NODE_STATE) != State.healthy:
                broken.append(node_name)
        if not broken:
            return State.healthy, broken
        if len(broken) == len(self._node_states):
            return State.down, broken
        return State.damaged, broken
