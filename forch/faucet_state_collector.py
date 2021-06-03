"""Processing faucet events"""
# pylint: disable=too-many-lines

import copy
from datetime import datetime
import json
import time
import threading

# TODO: Clean up to use State enum
from forch.constants import \
    STATE_UP, STATE_INITIALIZING, STATE_DOWN, STATE_ACTIVE, STATE_BROKEN
from forch.utils import dict_proto, get_logger

from forch.proto.dataplane_state_pb2 import DataplaneState
from forch.proto.devices_state_pb2 import DevicePlacement
from forch.proto.faucet_event_pb2 import StackTopoChange
from forch.proto.host_path_pb2 import HostPath
from forch.proto.list_hosts_pb2 import HostList
from forch.proto.shared_constants_pb2 import DVAState, LacpState, State, LacpRole
from forch.proto.switch_state_pb2 import SwitchState
from forch.proto.system_state_pb2 import StateSummary

LACP_TO_LINK_STATE = {
    LacpState.none: STATE_DOWN,
    LacpState.default: STATE_DOWN,
    LacpState.init: STATE_DOWN,
    LacpState.active: STATE_ACTIVE,
    LacpState.noact: STATE_UP,
}


def _dump_states(func):
    """Decorator to dump the current states after the states map is modified"""

    def _set_default(obj):
        if isinstance(obj, set):
            return list(obj)
        return obj

    def wrapped(self, *args, **kwargs):
        res = func(self, *args, **kwargs)
        with self.lock:
            # pylint: disable=protected-access
            self._logger.debug(json.dumps(self.switch_states, default=_set_default))
        return res

    return wrapped


_RESTORE_METHODS = {'port': {}, 'dp': {}}

LINK_SUBKEY_FORMAT = '%s:%s'
LINK_KEY_FORMAT = '%s@%s'
FAUCET_STACK_STATE_BAD = 2
FAUCET_STACK_STATE_UP = 3
SWITCH_CONNECTED = "CONNECTED"
SWITCH_DOWN = "DOWN"
INVALID_VLAN = 0

DP_ID = "dp_id"
PORTS = "ports"
PORT_STATE_COUNT = "change_count"
PORT_STATE_TS = "timestamp"
PORT_STATE_UP = "state_up"
PORT_STATE = "port_state"
LEARNED_MACS = "learned_macs"
MAC_LEARNING_SWITCH = "switches"
MAC_LEARNING_PORT = "port"
MAC_LEARNING_IP = "ip_address"
MAC_LEARNING_TS = "timestamp"
MAC_RADIUS_RESULT = "radius_result"
MAC_RADIUS_ACCESS = "access"
MAC_RADIUS_SEGMENT = "segment"
MAC_RADIUS_ROLE = "role"
CONFIG_CHANGE_COUNT = "config_change_count"
SW_STATE = "switch_state"
SW_STATE_LAST_CHANGE = "switch_state_last_change"
SW_STATE_CHANGE_COUNT = "switch_state_change_count"
LINK_STATE = "link_state"
TOPOLOGY_ENTRY = "topology"
TOPOLOGY_DPS = "dps"
TOPOLOGY_DPS_HASH = "dps_hash"
TOPOLOGY_CHANGE_COUNT = "topology_change_count"
TOPOLOGY_LAST_CHANGE = "topology_last_change"
LINKS_STATE = "links_state"
LINKS_GRAPH = "links_graph"
LINKS_HASH = "links_hash"
LINKS_CHANGE_COUNT = "links_change_count"
LINKS_LAST_CHANGE = "links_last_change"
TOPOLOGY_DP_MAP = "switches"
TOPOLOGY_LINK_MAP = "links"
TOPOLOGY_ROOT = "active_root"
DPS_CFG = "dps_config"
DPS_CFG_CHANGE_COUNT = "config_change_count"
DPS_CFG_CHANGE_TS = "config_change_timestamp"
EGRESS_STATE = "egress_state"
EGRESS_DETAIL = "egress_state_detail"
EGRESS_LAST_CHANGE = "egress_state_last_change"
EGRESS_CHANGE_COUNT = "egress_state_change_count"
EGRESS_LINK_MAP = "links"
VLAN_STATES = "vlan_states"
VLANS = "vlans"
PACKET_COUNTS = "packet_counts"
PACKET_RATE_STATE = "packet_rate_state"

VLAN_PACKET_COUNT_METRIC = 'flow_packet_count_vlan'


# pylint: disable=too-many-public-methods
class FaucetStateCollector:
    """Processing faucet events and store states in the map"""
    def __init__(self, config, is_faucetizer_enabled):
        self.switch_states = {}
        self.topo_state = {}
        self.learned_macs = {}
        self.faucet_config = {}
        self.packet_counts = {}
        self.radius_results = {}
        self.lock = threading.RLock()
        self._lock = threading.Lock()
        self._logger = get_logger('fstate')
        self.process_lag_state(time.time(), None, None, False, False)
        self._is_faucetizer_enabled = is_faucetizer_enabled
        self._is_state_restored = False
        self._state_restore_error = "Initializing"
        self._placement_callback = None
        self._get_gauge_metrics = None
        self._get_dva_state = None
        self._stack_state_event = 0
        self._stack_state_update = 0
        self._stack_state_data = None
        self._forch_metrics = None
        self._device_state_reporter = None
        self._config = config
        self._change_coalesce_sec = config.event_client.stack_topo_change_coalesce_sec
        self._packet_per_sec_thresholds = config.dataplane_monitoring.vlan_pkt_per_sec_thresholds

    def set_state_restored(self, is_restored, restore_error=None):
        """Set state restore result"""
        with self._lock:
            self._is_state_restored = is_restored
            self._state_restore_error = restore_error

    def heartbeat_update_stack_state(self):
        """Check for any necessary periodic updates"""
        if not self._stack_state_data:
            return
        time_now = time.time()
        event_delta = time_now - self._stack_state_event
        update_delta = time_now - self._stack_state_update
        if event_delta > self._change_coalesce_sec or update_delta > self._change_coalesce_sec * 2:
            self._logger.warning('stack_state_links update apply %ds', update_delta)
            self._stack_state_update = 0
            state_data, self._stack_state_data = (self._stack_state_data, None)
            self._update_stack_topo_state_raw(*state_data)
        else:
            self._logger.warning('stack_state_links update ignore %ds', event_delta)

    def _get_packet_counts_from_samples(self, metric_samples):
        vlan_counts = {}
        for sample in metric_samples:
            vlan_str = sample.labels['vlan']
            vlan_id = int(vlan_str) if vlan_str else 0
            vlan_counts[vlan_id] = vlan_counts.get(vlan_id, 0) + int(sample.value)
        return vlan_counts

    def _update_packet_count_states(self, vlan_counts, interval):
        for vlan_id, vlan_count in vlan_counts.items():
            last_vlan_map = self.packet_counts.setdefault(vlan_id, {})
            last_vlan_count = last_vlan_map.get(PACKET_COUNTS)
            last_vlan_map[PACKET_COUNTS] = vlan_count

            self._forch_metrics.update_var(
                'dataplane_packet_count_vlan', vlan_count, labels=[vlan_id])

            if last_vlan_count is None:
                continue

            rate = (vlan_count - last_vlan_count) / interval
            threshold = self._packet_per_sec_thresholds.get(vlan_id)

            if not threshold:
                rate_state = State.unknown
            elif rate > threshold:
                self._logger.error(
                    'Packet per sec for vlan %d is greater than threshold %d: %.2f',
                    vlan_id, threshold, rate)
                rate_state = State.broken
            else:
                rate_state = State.healthy

            last_vlan_map[PACKET_RATE_STATE] = rate_state
            self._forch_metrics.update_var(
                'dataplane_packet_rate_state_vlan', rate_state, labels=[vlan_id])

    def heartbeat_update_packet_count(self, interval, get_metrics):
        """Evaluate packet count change rate for each switch and vlan"""
        if not self._packet_per_sec_thresholds:
            return

        packet_count_metric = get_metrics([VLAN_PACKET_COUNT_METRIC]).get(VLAN_PACKET_COUNT_METRIC)
        if not packet_count_metric:
            self._logger.warning('No %s metric available', VLAN_PACKET_COUNT_METRIC)
            return

        vlan_counts = self._get_packet_counts_from_samples(packet_count_metric.samples)

        with self._lock:
            self._update_packet_count_states(vlan_counts, interval)

    def _make_summary(self, state, detail):
        summary = StateSummary()
        summary.state = state
        summary.detail = detail
        return summary

    # pylint: disable=no-self-argument, protected-access, no-method-argument
    def _pre_check():
        def pre_check(func):
            def wrapped(self, *args, **kwargs):
                with self._lock:
                    if not self._is_state_restored:
                        detail = f'State is not restored: {self._state_restore_error}'
                        return self._make_summary(State.broken, detail)
                    try:
                        return func(self, *args, **kwargs)
                    except Exception as e:
                        self._logger.exception(e)
                        return self._make_summary(State.broken, str(e))
            return wrapped
        return pre_check

    # pylint: disable=no-self-argument
    def _register_restore_state_method(label_name, metric_name):
        def register(func):
            _RESTORE_METHODS[label_name][metric_name] = func
            return func
        return register

    def restore_states_from_metrics(self, metrics):
        """Restore internal states from prometheus metrics"""
        self._logger.info('restoring internal state from metrics')
        current_time = time.time()
        for label_name, method_map in _RESTORE_METHODS.items():
            for metric_name, restore_method in method_map.items():
                if metric_name not in metrics:
                    self._logger.warning("Metrics does not contain: %s", metric_name)
                    continue
                for sample in metrics[metric_name].samples:
                    switch = sample.labels['dp_name']
                    label = int(sample.labels.get(label_name, 0))
                    restore_method(self, current_time, switch, label, int(sample.value))
        self._restore_lag_state_from_metrics(metrics)
        self._restore_dataplane_state_from_metrics(metrics)
        self._restore_l2_learn_state_from_samples(metrics['learned_l2_port'].samples)
        self._restore_dp_config_change(metrics)
        return int(metrics['faucet_event_id'].samples[0].value)

    def _restore_l2_learn_state_from_samples(self, samples):
        self._cleanup_learned_macs()

        timestamp = time.time()
        ports_learned = False

        for sample in samples:
            dp_name = sample.labels['dp_name']
            port = int(sample.value)
            eth_src = sample.labels['eth_src']
            vid = int(sample.labels.get('vid', INVALID_VLAN))
            if port:
                self.process_port_learn(timestamp, dp_name, port, eth_src, vid)
                ports_learned = True
        if not ports_learned:
            self._logger.info('No learned ports restored.')
            return

    def _restore_dataplane_state_from_metrics(self, metrics):
        """Restores dataplane state from prometheus metrics. relies on STACK_STATE being restored"""
        link_graph, stack_root, dps, timestamp = [], "", {}, ""
        topo_map = self._get_topo_map(False)
        for key, status in topo_map.items():
            if status.get(LINK_STATE) in (STATE_ACTIVE, STATE_UP):
                item = self._topo_map_to_link_graph(key)
                if item:
                    link_graph.append(item)

        samples = metrics.get('faucet_stack_root_dpid').samples
        assert samples, 'no faucet_stack_root_dpid samples fount'

        # stack root from varz is dpid, need to convert to dp_name
        stack_root_id = samples[0].value
        stack_root = None

        for sample in metrics.get('dp_root_hop_port').samples:
            switch = sample.labels.get('dp_name')
            # convert dp_id to dp_name
            if stack_root_id == int(sample.labels.get('dp_id'), 16):
                stack_root = switch
            stack_dp = StackTopoChange.StackDp(root_hop_port=int(sample.value))
            dps[switch] = stack_dp

        timestamp = time.time()
        self._update_stack_topo_state(timestamp, link_graph, stack_root, dps)

    def _restore_lag_state_from_metrics(self, metrics):
        """Restores dataplane state from prometheus metrics. Relies on STACK_STATE being restored"""
        for sample in metrics.get('port_lacp_state').samples:
            switch = sample.labels.get('dp_name')
            port = sample.labels.get('port')
            port_attr = self._get_port_attributes(switch, port)
            if not port_attr:
                continue
            port_type = port_attr['type']
            if port_type != 'egress':
                continue
            role_sample = [sample for sample in metrics.get('port_lacp_role').samples
                           if sample.labels.get('dp_name') == switch and
                           sample.labels.get('port') == port][0]
            timestamp = time.time()
            self.process_lag_state(timestamp, switch, port, role_sample.value, sample.value)

    def _restore_dp_config_change(self, metrics):
        with self.lock:
            cold_reload_samples = metrics['faucet_config_reload_cold'].samples
            warm_reload_samples = metrics['faucet_config_reload_warm'].samples

            for sample in cold_reload_samples + warm_reload_samples:
                dp_id = sample.labels['dp_name']
                dp_state = self.switch_states.setdefault(dp_id, {})
                change_count = dp_state.get(CONFIG_CHANGE_COUNT, 0) + sample.value
                dp_state[DP_ID] = dp_id
                dp_state[CONFIG_CHANGE_COUNT] = change_count

                self._logger.info(
                    'Restored dp_config_change of switch %s with change count %d',
                    dp_id, change_count)

    def _topo_map_to_link_graph(self, item):
        """Conver topo map item to a link map item"""
        # TODO: Use regex to validate key format
        dp_ports = item.split('@')
        linkobj = None
        assert len(dp_ports) == 2, "link key does not match expected format."
        dp_a, port_a = dp_ports[0].split(':')
        dp_z, port_z = dp_ports[1].split(':')
        key = "%s:%s-%s:%s" % (dp_a, port_a, dp_z, port_z)
        port_a = "Port "+port_a
        port_z = "Port "+port_z
        port_map = StackTopoChange.LinkPortMap(dp_a=dp_a, port_a=port_a, dp_z=dp_z, port_z=port_z)
        linkobj = StackTopoChange.StackLink(key=key, source=dp_a, target=dp_z, port_map=port_map)
        return linkobj

    @_pre_check()
    def get_dataplane_summary(self):
        """Get summary of dataplane"""
        dplane_state = self._get_dataplane_state()
        state_summary = self._make_summary(dplane_state.dataplane_state,
                                           dplane_state.dataplane_state_detail)
        state_summary.change_count = dplane_state.dataplane_state_change_count
        state_summary.last_change = dplane_state.dataplane_state_last_change
        return state_summary

    def _update_dataplane_detail(self, dplane_state):
        detail = []
        state = STATE_INITIALIZING

        egress = dplane_state.get('egress', {})
        egress_state = egress.get(EGRESS_STATE)
        egress_detail = egress.get(EGRESS_DETAIL)

        detail.append("egress: " + str(egress_detail))
        state = egress_state

        broken_sw = self._get_broken_switches(dplane_state)
        if broken_sw:
            state = State.broken
            detail.append("broken switches: " + str(broken_sw))

        broken_links = self._get_broken_links(dplane_state)
        if broken_links:
            state = State.broken
            detail.append("broken links: " + str(broken_links))

        broken_vlans = self._get_broken_vlans(dplane_state)
        if broken_vlans:
            state = State.broken
            detail.append('broken vlans: ' + str(broken_vlans))

        dplane_state['dataplane_state'] = state
        dplane_state['dataplane_state_detail'] = "; ".join(detail)

    @_pre_check()
    def get_dataplane_state(self):
        """get the topology state"""
        return self._get_dataplane_state()

    def _get_dataplane_state(self):
        """get the topology state impl"""
        dplane_state = {}
        change_counts = []
        last_change = '#n/a'  # Clevery chosen to be sorted less than timestamp.

        switch_map = self._get_switch_map()
        dplane_state['switch'] = switch_map
        change_counts.append(switch_map.get(SW_STATE_CHANGE_COUNT, 0))
        last_change = max(last_change, switch_map.get(SW_STATE_LAST_CHANGE, ''))

        stack_topo = self._get_stack_topo()
        dplane_state['stack'] = stack_topo
        change_counts.append(stack_topo.get(LINKS_CHANGE_COUNT, 0))
        last_change = max(last_change, stack_topo.get(LINKS_LAST_CHANGE, ''))

        egress_state = dplane_state.setdefault('egress', {})
        self._fill_egress_state(egress_state)
        change_counts.append(egress_state.get(EGRESS_CHANGE_COUNT, 0))
        last_change = max(last_change, egress_state.get(EGRESS_LAST_CHANGE, ''))

        vlan_states = {}
        for vlan_id, vlan_map in self.packet_counts.items():
            vlan_state = vlan_states.setdefault(vlan_id, {})
            vlan_state[PACKET_RATE_STATE] = vlan_map.get(PACKET_RATE_STATE)
        dplane_state[VLANS] = vlan_states

        self._update_dataplane_detail(dplane_state)
        dplane_state['dataplane_state_change_count'] = sum(change_counts)
        dplane_state['dataplane_state_last_change'] = last_change

        self._logger.info('dataplane_state_change_count sources: %s', change_counts)

        return dict_proto(dplane_state, DataplaneState)

    def _get_broken_switches(self, dplane_state):
        broken_sw = []
        sw_map = dplane_state.get('switch', {}).get(TOPOLOGY_DP_MAP, {})
        for switch, state in sw_map.items():
            if state.get(SW_STATE) == STATE_DOWN:
                broken_sw.append(switch)
        return broken_sw

    def _get_broken_links(self, dplane_state):
        broken_links = []
        link_map = dplane_state.get('stack', {}).get(TOPOLOGY_LINK_MAP, {})
        for link, link_obj in link_map.items():
            if link_obj.get(LINK_STATE) not in {STATE_ACTIVE, STATE_UP}:
                broken_links.append(link)
        broken_links.sort()
        return broken_links

    def _get_broken_vlans(self, dplane_state):
        broken_vlans = []
        vlan_states = dplane_state.get('vlans')
        for vlan_id, vlan_state in vlan_states.items():
            if vlan_state.get(PACKET_RATE_STATE) == State.broken:
                broken_vlans.append(vlan_id)
        broken_vlans.sort()
        return broken_vlans

    @_pre_check()
    def get_switch_summary(self):
        """Get summary of switch state"""
        switch_state = self._get_switch_state(None, None)
        state_summary = StateSummary()
        state_summary.state = switch_state.switch_state
        state_summary.detail = switch_state.switch_state_detail
        state_summary.change_count = switch_state.switch_state_change_count
        state_summary.last_change = switch_state.switch_state_last_change
        return state_summary

    def _augment_mac_urls(self, url_base, switch_data):
        if url_base:
            for mac, mac_data in switch_data.get('access_port_macs', {}).items():
                mac_data['url'] = f"{url_base}/?list_hosts?eth_src={mac}"

    @_pre_check()
    def get_switch_state(self, switch, port, url_base=None):
        """get a set of all switches"""
        return self._get_switch_state(switch, port, url_base)

    # pylint: disable=too-many-locals
    def _get_switch_state(self, switch, port, url_base=None):
        """Get switch state impl"""
        switches_data = {}
        broken = []
        change_count = 0
        last_change = '#n/a'  # Clevery chosen to be sorted less than timestamp.

        metrics = self._get_gauge_metrics()

        for switch_name in self.switch_states:
            arg_port = port if switch_name == switch else None
            switch_data = self._get_switch(switch_name, arg_port, metrics)
            switches_data[switch_name] = switch_data
            change_count += switch_data.get(SW_STATE_CHANGE_COUNT, 0)
            last_change = max(last_change, switch_data.get(SW_STATE_LAST_CHANGE, ''))
            if switch_data[SW_STATE] != STATE_ACTIVE:
                broken.append(switch_name)
            self._augment_mac_urls(url_base, switch_data)

        if not self.switch_states:
            switch_state = State.broken
            state_detail = 'No switches connected'
        elif broken:
            switch_state = State.broken
            state_detail = 'Switches in broken state: ' + ', '.join(broken)
        else:
            switch_state = State.healthy
            state_detail = None

        result = {
            'switch_state': switch_state,
            'switch_state_detail': state_detail,
            'switch_state_change_count': change_count,
            'switch_state_last_change': last_change,
            'switches': switches_data
        }

        if switch:
            result['switches'] = {switch: switches_data[switch]}
            result['switches_restrict'] = switch

        return dict_proto(result, SwitchState)

    def cleanup(self):
        """Clean up internal data"""
        with self.lock:
            self._cleanup_learned_macs()

    def _cleanup_learned_macs(self):
        """Clean up leanred macs"""
        with self._lock:
            old_learned_macs = copy.deepcopy(self.learned_macs)
            timestamp = time.time()

            for mac, mac_map in old_learned_macs.items():
                for switch_name, switch_map in mac_map.get(MAC_LEARNING_SWITCH, {}).items():
                    port = switch_map.get(MAC_LEARNING_PORT)
                    if port:
                        self.process_port_expire(timestamp, switch_name, port, mac)

    def _fill_egress_state(self, target_obj):
        """Return egress state obj"""
        with self.lock:
            egress_obj = self.topo_state.get('egress', {})
            if EGRESS_STATE not in egress_obj:
                target_obj[EGRESS_STATE] = State.unknown
                target_obj[EGRESS_DETAIL] = 'No LAG information received'
            else:
                target_obj[EGRESS_STATE] = egress_obj[EGRESS_STATE]
                target_obj[EGRESS_DETAIL] = egress_obj.get(EGRESS_DETAIL)
                target_obj[EGRESS_LAST_CHANGE] = egress_obj.get(EGRESS_LAST_CHANGE)
                target_obj[EGRESS_CHANGE_COUNT] = egress_obj.get(EGRESS_CHANGE_COUNT)

            target_obj[TOPOLOGY_ROOT] = self.topo_state.get(TOPOLOGY_ROOT)
            target_obj[EGRESS_LINK_MAP] = copy.deepcopy(egress_obj.get(EGRESS_LINK_MAP))

    def _get_switch_map(self):
        """returns switch map for topology overview"""
        switch_map = {}
        switch_map_obj = {}
        if not self.switch_states:
            return {}
        change_count = 0
        last_change = '#n/a'  # Clevery chosen to be sorted less than timestamp.
        with self.lock:
            for switch, switch_state in self.switch_states.items():
                switch_map[switch] = {}
                current_state = switch_state.get(SW_STATE)
                change_count += switch_state.get(SW_STATE_CHANGE_COUNT, 0)
                last_change = max(last_change, switch_state.get(SW_STATE_LAST_CHANGE, ''))
                if not current_state:
                    switch_map[switch][SW_STATE] = None
                elif current_state == SWITCH_CONNECTED:
                    switch_map[switch][SW_STATE] = STATE_ACTIVE
                else:
                    switch_map[switch][SW_STATE] = STATE_DOWN
            switch_map_obj[TOPOLOGY_DP_MAP] = switch_map
            switch_map_obj[SW_STATE_CHANGE_COUNT] = change_count
            switch_map_obj[SW_STATE_LAST_CHANGE] = last_change
            return switch_map_obj

    def _get_switch(self, switch_name, port, metrics):
        """lock protect get_switch_raw"""
        with self.lock:
            return self._get_switch_raw(switch_name, port, metrics)

    def _get_switch_config(self, switch_name):
        if switch_name not in self.faucet_config.get(DPS_CFG, {}):
            raise Exception(f'Missing switch configuration for {switch_name}')
        return self.faucet_config[DPS_CFG][switch_name]

    def _get_switch_raw(self, switch_name, port, metrics):
        """get switches state"""
        switch_map = {}

        # filling switch attributes
        switch_states = self.switch_states.get(switch_name)
        attributes_map = switch_map.setdefault("attributes", {})
        switch_config = self._get_switch_config(switch_name)
        attributes_map["dp_id"] = switch_config.dp_id

        # filling switch dynamics
        switch_map["restart_event_count"] = switch_states.get(CONFIG_CHANGE_COUNT)

        if switch_states.get(SW_STATE) == SWITCH_CONNECTED:
            switch_map[SW_STATE] = STATE_ACTIVE
        else:
            switch_map[SW_STATE] = STATE_DOWN
        switch_map[SW_STATE_LAST_CHANGE] = switch_states.get(SW_STATE_LAST_CHANGE, '')
        switch_map[SW_STATE_CHANGE_COUNT] = switch_states.get(SW_STATE_CHANGE_COUNT, 0)

        # filling port information
        switch_port_map = switch_map.setdefault('ports', {})
        if port:
            port_id = int(port)
            switch_port_map[port_id] = self._get_port_state(switch_name, port_id)
            switch_map['ports_restrict'] = port_id
            self._fill_port_behavior(switch_name, port_id, switch_port_map[port_id], metrics)
        else:
            for port_id in switch_states.get(PORTS, {}):
                switch_port_map[port_id] = self._get_port_state(switch_name, port_id)
                self._fill_port_behavior(
                    switch_name, port_id, switch_port_map[port_id], metrics)

        # filling packet rate
        for vlan_id, vlan_states in switch_states.get(VLAN_STATES, {}).items():
            packet_rate_state = vlan_states.get(PACKET_RATE_STATE)
            if packet_rate_state:
                vlan_map = switch_map.setdefault('vlans', {}).setdefault(vlan_id, {})
                vlan_map['packet_rate_state'] = packet_rate_state

        self._fill_learned_macs(switch_name, switch_map)
        self._fill_path_to_root(switch_name, switch_map)
        self._fill_switch_vlan_behavior(switch_name, switch_map, metrics)

        return switch_map

    def _get_port_state(self, switch: str, port: int):
        """Get port state"""
        # port attributes
        if port not in self.switch_states.get(str(switch), {}).get(PORTS, {}):
            return None
        port_states = self.switch_states[str(switch)][PORTS][port]
        port_map = {}
        port_attr = self._get_port_attributes(switch, port)
        switch_port_attributes_map = port_map.setdefault("attributes", {})
        switch_port_attributes_map["description"] = port_attr.get('description')
        switch_port_attributes_map["port_type"] = port_attr.get('type')
        switch_port_attributes_map["stack_peer_switch"] = str(port_attr.get('peer_switch'))
        peer_port = port_attr.get('peer_port')
        peer_port_number = peer_port.number if peer_port else None
        switch_port_attributes_map["stack_peer_port"] = peer_port_number

        # port dynamics
        if PORT_STATE_UP in port_states:
            port_up = port_states[PORT_STATE_UP]
            port_map[PORT_STATE] = STATE_UP if port_up else STATE_DOWN
        else:
            port_map[PORT_STATE] = None
        port_map["state_last_change"] = port_states.get(PORT_STATE_TS)
        port_map["state_change_count"] = port_states.get(PORT_STATE_COUNT)

        return port_map

    def _fill_learned_macs(self, switch_name, switch_map):
        """fills learned macs"""
        switch_states = self.switch_states.get(str(switch_name), {})
        for mac in switch_states.get(LEARNED_MACS, set()):
            mac_states = self.learned_macs.get(mac, {})
            learned_switch = mac_states.get(MAC_LEARNING_SWITCH, {}).get(switch_name, {})
            learned_port = learned_switch.get(MAC_LEARNING_PORT, None)
            if not learned_port:
                continue

            port_attr = self._get_port_attributes(switch_name, learned_port)
            if not port_attr:
                continue

            switch_learned_mac_map = None
            port_type = port_attr['type']
            if port_type in ('access', 'sequester'):
                switch_learned_mac_map = switch_map.setdefault('access_port_macs', {})
            elif port_type == 'stack':
                switch_learned_mac_map = switch_map.setdefault('stacking_port_macs', {})
            elif port_type == 'egress':
                switch_learned_mac_map = switch_map.setdefault('egress_port_macs', {})
            else:
                raise Exception('Unknown port type %s' % port_type)

            mac_map = switch_learned_mac_map.setdefault(mac, {})
            mac_map["mac_ips"] = list(mac_states.get(MAC_LEARNING_IP, []))
            mac_map["port"] = learned_port
            mac_map["timestamp"] = learned_switch.get(MAC_LEARNING_TS, None)

    def _fill_path_to_root(self, switch_name, switch_map):
        """populate path to root for switch_state"""
        switch_map["root_path"] = self.get_switch_egress_path(switch_name)

    def _fill_switch_vlan_behavior(self, switch_name, switch_map, metrics=None):
        dp_config = self.faucet_config.get(DPS_CFG, {}).get(switch_name)
        if not dp_config:
            self._logger.warning('Switch not defined in dps config: %s', switch_name)
            return

        vlans_map = switch_map.setdefault('vlans', {})

        for vid, vlan_config in dp_config.vlans.items():
            if not vlan_config.acls_in:
                continue

            acl_maps_list = vlans_map.setdefault(int(vid), {}).setdefault('acls', [])

            if metrics is None:
                self._fill_acls_behavior(switch_name, acl_maps_list, vlan_config.acls_in)
            else:
                assert 'flow_packet_count_vlan_acl' in metrics, (
                    f'VLAN ACL metric is not available for VLAN {vid}')

                samples = metrics['flow_packet_count_vlan_acl'].samples
                self._fill_acls_behavior(switch_name, acl_maps_list, vlan_config.acls_in, samples)

    def _fill_port_behavior(self, switch_name, port_id, port_map, metrics=None):
        dp_config = self.faucet_config.get(DPS_CFG, {}).get(switch_name)
        if not dp_config:
            self._logger.warning('Switch not defined in dps config: %s', switch_name)
            return

        port_config = dp_config.ports.get(port_id)
        if not port_config:
            raise Exception('Port not defined in dps config: %s, %s' % (switch_name, port_id))

        if port_config.native_vlan:
            port_map['dva_state'] = self._get_dva_state(switch_name, port_id) or DVAState.initial
            vlan_samples = metrics['flow_packet_count_vlan'].samples if metrics else None
            self._fill_port_vlan_behavior(
                port_map, switch_name, port_id, port_config.native_vlan, vlan_samples)

        if port_config.acls_in:
            acl_maps_list = port_map.setdefault('acls', [])

            if metrics is None:
                self._fill_acls_behavior(
                    switch_name, acl_maps_list, port_config.acls_in, None, port_id)
            else:
                assert 'flow_packet_count_port_acl' in metrics, 'No port acl metric available'

                port_acl_samples = metrics['flow_packet_count_port_acl'].samples
                self._fill_acls_behavior(
                    switch_name, acl_maps_list, port_config.acls_in, port_acl_samples, port_id)

    # pylint: disable=too-many-arguments
    def _fill_acls_behavior(self, switch_name, acls_map_list, acls_config,
                            metric_samples=None, port_id=None):
        for acl_config in acls_config:
            acl_map = {'name': acl_config._id}
            rules_map_list = acl_map.setdefault('rules', [])

            for rule_config in acl_config.rules:
                cookie_num = rule_config.get('cookie')
                rule_map = {'description': rule_config.get('description')}
                rules_map_list.append(rule_map)

                if not self._is_faucetizer_enabled or not metric_samples:
                    continue

                if not cookie_num:
                    raise Exception(f'Cookie is not generated for acl {acl_config._id}')

                has_sample = False
                for sample in metric_samples:
                    if str(sample.labels.get('cookie')) != str(cookie_num):
                        continue
                    if sample.labels.get('dp_name') != switch_name:
                        continue
                    if port_id and int(sample.labels.get('in_port')) != port_id:
                        continue
                    rule_map['packet_count'] = int(sample.value)
                    has_sample = True
                    break

                if not has_sample:
                    self._logger.debug(
                        'No ACL metric sample available for switch, port, ACL, rule:'
                        '%s, %s, %s, %s', switch_name, port_id, acl_config._id, cookie_num)

            acls_map_list.append(acl_map)

    def _fill_port_vlan_behavior(self, port_map, switch_name, port_id,
                                 vlan_config, metric_samples=None):
        vlan_map = port_map.setdefault('vlan', {})
        vlan_map['vlan_id'] = int(vlan_config.vid)

        if not metric_samples:
            return

        vlan_map['packet_count'] = 0
        has_sample = False
        for sample in metric_samples:
            if sample.labels.get('dp_name') != switch_name:
                continue
            in_port = sample.labels.get('in_port')
            if not in_port or int(in_port) != port_id:
                continue
            vlan_map['packet_count'] += int(sample.value)
            has_sample = True

        if not has_sample:
            self._logger.debug(
                'No VLAN metric sample available for switch, port: %s, %s', switch_name, port_id)

    @staticmethod
    def _make_key(start_dp, start_port, peer_dp, peer_port):
        subkey1 = LINK_SUBKEY_FORMAT % (start_dp, start_port)
        subkey2 = LINK_SUBKEY_FORMAT % (peer_dp, peer_port)
        return LINK_KEY_FORMAT % ((subkey1, subkey2) if subkey1 < subkey2 else (subkey2, subkey1))

    def _get_topo_map(self, check_active=True):
        topo_map = {}
        dps_objs = self.faucet_config.get(DPS_CFG, {}).values()
        if not dps_objs:
            return None
        for local_dp in dps_objs:
            for local_port, iface_obj in local_dp.interfaces.items():
                if 'stack' not in iface_obj:
                    continue
                peer_dp = iface_obj['stack']['dp']
                peer_port = iface_obj['stack']['port'].number
                if peer_dp and peer_port:
                    key = self._make_key(local_dp, local_port, peer_dp, peer_port)
                    if key not in topo_map:
                        if check_active:
                            state = self._get_link_state(local_dp, local_port, peer_dp, peer_port)
                        else:
                            state = self._get_base_link_state(local_dp, local_port)
                        topo_map.setdefault(key, {})[LINK_STATE] = state
        return topo_map

    def _get_link_state(self, local_dp, local_port, peer_dp, peer_port):
        local_dp = str(local_dp)
        local_port = int(local_port)
        peer_dp = str(peer_dp)
        peer_port = int(peer_port)
        dps = self.topo_state.get(TOPOLOGY_DPS, {})
        if (dps[local_dp].root_hop_port == local_port or
                dps[peer_dp].root_hop_port == peer_port):
            return STATE_ACTIVE
        return self._get_base_link_state(local_dp, local_port)

    def _get_base_link_state(self, local_dp, local_port):
        local_dp = str(local_dp)
        local_port = int(local_port)
        dp_state = self.topo_state.setdefault(LINKS_STATE, {}).setdefault(local_dp, {})
        port_state = dp_state.setdefault(local_port, {}).get('state')
        if port_state == FAUCET_STACK_STATE_UP:
            return STATE_UP
        if port_state == FAUCET_STACK_STATE_BAD:
            return STATE_BROKEN
        return STATE_DOWN

    def _get_stack_topo(self):
        """Returns formatted topology object"""
        with self.lock:
            dps = self.topo_state.get(TOPOLOGY_DPS, {})
            if not dps:
                return {}
            topo_map_obj = {}
            topo_map_obj[TOPOLOGY_LINK_MAP] = self._get_topo_map()
            topo_map_obj[LINKS_CHANGE_COUNT] = self.topo_state.get(LINKS_CHANGE_COUNT, 0)
            topo_map_obj[LINKS_LAST_CHANGE] = self.topo_state.get(LINKS_LAST_CHANGE)
        return topo_map_obj

    def _is_port_up(self, switch, port):
        """Check if port is up"""
        with self.lock:
            return self.switch_states.get(str(switch), {})\
                    .get(PORTS, {}).get(port, {}).get('state_up', False)

    def get_active_egress_path(self, src_mac):
        """Given a MAC address return active route to egress."""
        src_switch, src_port = self._get_access_switch(src_mac)
        if not src_switch or not src_port:
            return self._make_summary(
                State.broken, f'Device {src_mac} is not connected to access switch')
        egress_path_state = self.get_switch_egress_path(src_switch, src_port)
        egress_path = egress_path_state.get('path')
        if egress_path:
            return dict_proto({
                'src_ips': list(self.learned_macs.get(src_mac, {}).get(MAC_LEARNING_IP, [])),
                'path': egress_path
            }, HostPath)
        return self._make_summary(
            egress_path_state['path_state'], egress_path_state['path_state_detail'])

    def get_switch_egress_path(self, src_switch, src_port=None):
        """"Returns path to egress from given switch. Appends ingress port to first hop if given"""
        with self.lock:
            link_list = self.topo_state.get(LINKS_GRAPH)
            dps = self.topo_state.get(TOPOLOGY_DPS)

            if link_list is None or dps is None:
                return {
                    'path_state': State.broken,
                    'path_state_detail': 'Missing topology dps or links'
                }
            if not link_list or not dps:
                return {
                    'path_state': State.broken,
                    'path_state_detail': 'No active links available'
                }

            hop = {'switch': src_switch}

            if src_port:
                hop['in'] = src_port

            path, error_detail = self._populate_path(hop, dps, link_list)

            if not error_detail:
                return {'path_state': State.healthy, 'path': path}

            return {
                'path_state': State.broken,
                'path_state_detail': ('No path to root found. ' + error_detail).strip()
            }

    def _populate_path(self, hop, dps, link_list):
        path = []
        visited_hops = set()
        while hop:
            next_hop = {}
            hop_switch = hop['switch']
            egress_port = dps[hop_switch].root_hop_port

            if egress_port:
                hop['out'] = egress_port
                self._populate_hop(link_list, hop, next_hop, egress_port)
                path.append(hop)
            elif hop_switch == self.topo_state.get(TOPOLOGY_ROOT):
                hop['out'] = self._get_egress_port(hop_switch)
                path.append(hop)
                return path, ''
            hop_tuple = tuple(hop.values())
            if hop_tuple in visited_hops:
                return path, 'Loop in topology.'
            visited_hops.add(hop_tuple)
            hop = next_hop
        return path, 'Root absent in topology.'

    def _populate_hop(self, link_list, hop, next_hop, egress_port):
        hop_switch = hop['switch']
        for link_map in link_list:
            if not link_map:
                continue
            sw_1, port_1, sw_2, port_2 = (FaucetStateCollector.get_endpoints_from_link
                                          (link_map))
            if hop_switch == sw_1 and egress_port == port_1:
                next_hop['switch'] = sw_2
                next_hop['in'] = port_2
                return
            if hop_switch == sw_2 and egress_port == port_2:
                next_hop['switch'] = sw_1
                next_hop['in'] = port_1
                return

    def _get_host_path(self, src_mac, dst_mac):
        src_switch, src_port = self._get_access_switch(src_mac)
        dst_switch, dst_port = self._get_access_switch(dst_mac)
        switch_map = self.learned_macs[dst_mac][MAC_LEARNING_SWITCH]

        path = []
        current_switch = src_switch
        max_hops = 5
        while max_hops > 0:
            if current_switch not in switch_map:
                raise Exception('No route to host at %s' % current_switch)
            out_port = switch_map[current_switch][MAC_LEARNING_PORT]
            hop = {'switch': current_switch, 'in': src_port, 'out': out_port}
            path.append(hop)
            if current_switch == dst_switch:
                break
            link = self._get_port_attributes(current_switch, out_port)
            current_switch = str(link['peer_switch'])
            src_port = link['peer_port'].number
            max_hops -= 1

        if not max_hops:
            raise Exception('Forwarding loop detected: %s' % path)

        assert out_port == dst_port, 'last output port does not match destination port'

        return path

    @_pre_check()
    def get_host_path(self, src_mac, dst_mac, to_egress):
        """Given two MAC addresses in the core network, find the active path between them"""
        if not src_mac:
            return self._make_summary(
                State.broken, 'Empty eth_src. Please use list_hosts to get a list of hosts')

        if not dst_mac and not to_egress:
            return self._make_summary(
                State.broken, 'Empty eth_dst. Use list_hosts, or set to_egress=true')

        if src_mac not in self.learned_macs or dst_mac and dst_mac not in self.learned_macs:
            error_msg = 'MAC address cannot be found. Please use list_hosts to get a list of hosts'
            return self._make_summary(State.broken, error_msg)

        if to_egress:
            return self.get_active_egress_path(src_mac)

        res = {
            'src_ips': list(self.learned_macs[src_mac].get(MAC_LEARNING_IP, [])),
            'dst_ips': list(self.learned_macs[dst_mac].get(MAC_LEARNING_IP, [])),
            'path': self._get_host_path(src_mac, dst_mac)
        }

        return dict_proto(res, HostPath)

    @_dump_states
    @_register_restore_state_method(label_name='port', metric_name='port_status')
    def process_port_state(self, timestamp, name, port, state):
        """process port state event"""
        with self.lock:
            switch_config = self.faucet_config.get(DPS_CFG, {}).get(name)
            if not switch_config:
                self._forch_metrics.inc_var('unconfigured_port_event', labels=[name, port])
                self._logger.error('Switch %s is not in faucet config', name)
                return

            port_config = switch_config.interfaces.get(port)
            if not port_config:
                self._forch_metrics.inc_var('unconfigured_port_event', labels=[name, port])
                self._logger.error('Port %s is not in switch config %s', port, name)
                return

            port_table = self.switch_states\
                .setdefault(name, {})\
                .setdefault(PORTS, {})\
                .setdefault(port, {})

            port_table[PORT_STATE_UP] = state
            port_table[PORT_STATE_TS] = datetime.fromtimestamp(timestamp).isoformat()
            port_table[PORT_STATE_COUNT] = port_table.setdefault(PORT_STATE_COUNT, 0) + 1

            port_attr = self._get_port_attributes(name, port)
            if port_attr and port_attr['type'] == 'access':
                if not state and self._placement_callback:
                    device_placement = DevicePlacement(switch=name, port=port, connected=False)
                    self._placement_callback(None, device_placement)
                if self._device_state_reporter:
                    self._device_state_reporter.process_port_state(name, port, state)

            vid = port_config.get('native_vlan')
            self._logger.info(
                'port_state update: %s: %s, Up: %s, VLAN: %s', name, port, state, vid)

    def process_port_change(self, event):
        """Wrapper for process_port_state"""
        state = event.status and event.reason != 'DELETE'
        self.process_port_state(event.timestamp, event.dp_name, event.port_no, state)

    @_dump_states
    def process_lag_state(self, timestamp, name, port, lacp_role, lacp_state):
        """Process a lag state change"""
        with self.lock:
            self._logger.info(
                'lag_state update %s Port %s Role: %s State: %s',
                name, port, LacpRole.LacpRole.Name(int(lacp_role)),
                LacpState.LacpState.Name(int(lacp_state)))
            egress_state = self.topo_state.setdefault('egress', {})
            lacp_role = int(lacp_role)  # varz returns float. Need to convert to int
            lacp_state = int(lacp_state)  # varz returns float. Need to convert to int

            links = egress_state.setdefault(EGRESS_LINK_MAP, {})
            change_count = egress_state.setdefault(EGRESS_CHANGE_COUNT, 0)
            egress_state[EGRESS_LAST_CHANGE] = datetime.fromtimestamp(timestamp).isoformat()

            if not name or not self._is_egress_port(name, port):
                return

            key = '%s:%s' % (name, port)
            link = links.setdefault(key, {})
            link_state = self._get_lacp_link_state(lacp_role, lacp_state)

            if link_state != link.get(LINK_STATE):
                change_count = change_count + 1
                link[LINK_STATE] = link_state

            state, egress_detail = self._get_egress_state_detail(links)

            egress_state[EGRESS_CHANGE_COUNT] = change_count
            egress_state[EGRESS_STATE] = state
            egress_state[EGRESS_DETAIL] = egress_detail
            self._logger.info(
                'lag_state Change #%d %s, State: %s Egress detail: %s',
                change_count, name, State.State.Name(state), egress_detail)

    def _get_egress_state_detail(self, links):
        state_set = set()
        egress_name = None
        link_down = None
        for key, status in links.items():
            link_state = status.get(LINK_STATE)
            state_set.add(link_state)
            if link_state == STATE_ACTIVE:
                egress_name = key
            elif link_state != STATE_UP:
                link_down = key
        if state_set == set([STATE_ACTIVE, STATE_UP]) or state_set == set([STATE_ACTIVE]):
            state = State.healthy
        elif STATE_ACTIVE in state_set:
            state = State.damaged
        else:
            state = State.broken
        egress_postfix = ", %s down" % link_down if state == State.damaged else ""
        if state == State.broken:
            egress_detail = "All links down"
        else:
            egress_detail = str(egress_name) + str(egress_postfix)
        return state, egress_detail

    @_dump_states
    # pylint: disable=too-many-arguments
    def process_port_learn(self, timestamp, name, port, mac, vid, ip_addr=None):
        """process port learn event"""
        with self.lock:
            mac_entry = self.learned_macs.setdefault(mac, {})
            if ip_addr:
                mac_entry.setdefault(MAC_LEARNING_IP, set()).add(ip_addr)

            mac_switches = mac_entry.setdefault(MAC_LEARNING_SWITCH, {})
            learning_switch = mac_switches.setdefault(name, {})
            learning_switch[MAC_LEARNING_PORT] = port
            learning_switch[MAC_LEARNING_TS] = datetime.fromtimestamp(timestamp).isoformat()

            # update per switch mac table
            self.switch_states\
                .setdefault(name, {})\
                .setdefault(LEARNED_MACS, set())\
                .add(mac)

            self._logger.info(
                'Learned %s at %s:%s on vlan %s as %s', mac, name, port, vid, ip_addr)
            port_attr = self._get_port_attributes(name, port)

            radius_result = self.radius_results.get(mac)
            if radius_result:
                mac_entry[MAC_RADIUS_RESULT] = radius_result
            else:
                assert not mac_entry.get(MAC_RADIUS_RESULT)

            if port_attr and port_attr['type'] == 'access':
                if self._placement_callback:
                    device_placement = DevicePlacement(switch=name, port=port, connected=True)
                    self._placement_callback(mac, device_placement)

                if self._forch_metrics:
                    self._update_learned_macs_metric(mac, name, port)

                if self._device_state_reporter:
                    if vid and vid != INVALID_VLAN:
                        self._device_state_reporter.process_port_learn(name, port, mac, vid)
                    else:
                        self._logger.error(
                            'Device %s is not learned with a valid vlan: %d', mac, vid)

    @_dump_states
    def process_port_expire(self, timestamp, name, port, mac, expired_vlan=None):
        """process port expire event"""
        with self.lock:
            self._logger.info(
                'Learned entry %s on vlan %s at %s:%s expired.', mac, expired_vlan, name, port)

            port_attr = self._get_port_attributes(name, port)
            if port_attr and port_attr['type'] == 'access':
                if self._forch_metrics:
                    self._update_learned_macs_metric(mac, name, port, expire=True)

            switch_learned_macs = self.switch_states[name][LEARNED_MACS]
            if mac in switch_learned_macs:
                switch_learned_macs.remove(mac)
            else:
                self._logger.debug('Entry %s does not exist in learned macs dict', mac)

            if name in self.learned_macs.get(mac, {}).get(MAC_LEARNING_SWITCH, {}):
                self.learned_macs[mac][MAC_LEARNING_SWITCH].pop(name)
                if not self.learned_macs[mac][MAC_LEARNING_SWITCH]:
                    self.learned_macs.pop(mac)
            else:
                self._logger.debug('Entry %s does not exist in learned macs set', mac)

    @_dump_states
    def process_dp_config_change(self, timestamp, dp_name, restart_type, dp_id):
        """process config change event"""
        with self.lock:
            # No dp_id (or 0) indicates that this is system-wide, not for a given switch.
            if not dp_id:
                return

            dp_state = self.switch_states.setdefault(dp_name, {})
            change_count = dp_state.get(CONFIG_CHANGE_COUNT, 0) + 1
            self._logger.info('dp_config #%d %s change type %s', change_count, dp_id, restart_type)

            dp_state[DP_ID] = dp_id
            dp_state[CONFIG_CHANGE_COUNT] = change_count

    @_dump_states
    @_register_restore_state_method(label_name='dp', metric_name='dp_status')
    def process_dp_change(self, timestamp, dp_name, _, connected):
        """process dp_change to get dp state"""
        with self.lock:
            if not dp_name:
                return
            dp_state = self.switch_states.setdefault(dp_name, {})
            new_state = SWITCH_CONNECTED if connected else SWITCH_DOWN
            if dp_state.get(SW_STATE) != new_state:
                change_count = dp_state.get(SW_STATE_CHANGE_COUNT, 0) + 1
                self._logger.info(
                    'dp_change #%d %s, %s -> %s', change_count, dp_name, dp_state.get(SW_STATE),
                    new_state)
                dp_state[SW_STATE] = new_state
                dp_state[SW_STATE_LAST_CHANGE] = datetime.fromtimestamp(timestamp).isoformat()
                dp_state[SW_STATE_CHANGE_COUNT] = change_count

    @_dump_states
    def process_dataplane_config_change(self, timestamp, dps_config):
        """Handle config data sent through event channel """
        with self.lock:
            cfg_state = self.faucet_config
            change_count = cfg_state.get(DPS_CFG_CHANGE_COUNT, 0) + 1
            self._logger.info('dataplane_config #%d change: %r', change_count, dps_config)
            cfg_state[DPS_CFG] = {str(dp): dp for dp in dps_config}
            cfg_state[DPS_CFG_CHANGE_TS] = datetime.fromtimestamp(timestamp).isoformat()
            cfg_state[DPS_CFG_CHANGE_COUNT] = change_count

            self._update_learned_macs_metrics()

    @_dump_states
    @_register_restore_state_method(label_name='port', metric_name='port_stack_state')
    def process_stack_state(self, timestamp, dp_name, port, new_state):
        """Process a stack link state change"""
        with self.lock:
            links_state = self.topo_state.setdefault(LINKS_STATE, {})
            port_state = links_state.setdefault(dp_name, {}).setdefault(port, {})
            if port_state.get('state') != new_state:
                port_state['state'] = new_state
                link_change_count = self._update_stack_links_stats(timestamp)
                self._logger.info(
                    'stack_state_links #%d %s:%d is now %s', link_change_count, dp_name, port,
                    new_state)

    @_dump_states
    def process_stack_topo_change_event(self, topo_change):
        """Process stack topology change event"""
        link_graph = topo_change.graph.links
        stack_root = topo_change.stack_root
        dps = topo_change.dps
        timestamp = topo_change.timestamp
        self._update_stack_topo_state(timestamp, link_graph, stack_root, dps)

    def _update_stack_topo_state(self, timestamp, link_graph, stack_root, dps):
        """Update topo_state with stack topology information"""

        if self._change_coalesce_sec:
            self._stack_state_event = time.time()
            if not self._stack_state_update:
                self._stack_state_update = self._stack_state_event
            self._stack_state_data = (timestamp, link_graph, stack_root, dps)
            self._logger.warning('stack_state_links update save')
            return

        self._update_stack_topo_state_raw(timestamp, link_graph, stack_root, dps)

    def _update_stack_topo_state_raw(self, timestamp, link_graph, stack_root, dps):
        topo_state = self.topo_state
        with self.lock:
            links_hash = str(sorted(link_graph, key=lambda link: link.SerializeToString()))
            if topo_state.get(LINKS_HASH) != links_hash:
                topo_state[LINKS_GRAPH] = link_graph
                topo_state[LINKS_HASH] = links_hash
                link_change_count = self._update_stack_links_stats(timestamp)
                graph_links = [link.key for link in link_graph]
                graph_links.sort()
                self._logger.info(
                    'stack_state_links #%d links: %s', link_change_count, graph_links)

            msg_str = "root %s: %s" % (stack_root, self._list_root_hops(dps))
            prev_msg = topo_state.get(TOPOLOGY_DPS_HASH)
            if prev_msg != msg_str:
                topo_change_count = topo_state.get(TOPOLOGY_CHANGE_COUNT, 0) + 1
                self._logger.info('stack_topo_change #%d to %s', topo_change_count, msg_str)
                topo_state[TOPOLOGY_ROOT] = stack_root
                topo_state[TOPOLOGY_DPS] = dps
                topo_state[TOPOLOGY_DPS_HASH] = msg_str
                topo_state[TOPOLOGY_CHANGE_COUNT] = topo_change_count
                topo_state[TOPOLOGY_LAST_CHANGE] = datetime.fromtimestamp(timestamp).isoformat()

    def _list_root_hops(self, dps):
        root_hops = ['%s:%d' % (dp, dps[dp].root_hop_port) for dp in dps]
        root_hops.sort()
        return root_hops

    def _update_stack_links_stats(self, timestamp):
        link_change_count = self.topo_state.get(LINKS_CHANGE_COUNT, 0) + 1
        self.topo_state[LINKS_CHANGE_COUNT] = link_change_count
        self.topo_state[LINKS_LAST_CHANGE] = datetime.fromtimestamp(timestamp).isoformat()
        return link_change_count

    def _update_learned_macs_metrics(self):
        for mac in self.learned_macs:
            switch, port = self._get_access_switch(mac)
            if switch and port:
                self._update_learned_macs_metric(mac, switch, port)

    def _update_learned_macs_metric(self, mac, switch_name, port, expire=False):
        if not self.faucet_config.get(DPS_CFG):
            return

        port_map = {}
        self._fill_port_behavior(switch_name, port, port_map)
        vlan = port_map.get('vlan', 0)

        port = 0 if expire else port

        self._forch_metrics.update_var(
            'learned_l2_port', port,
            labels=[switch_name, mac, vlan])

    @staticmethod
    def get_endpoints_from_link(link_map):
        """Get the the pair of switch and port for a link"""
        from_sw = link_map.port_map.dp_a
        from_port = int(link_map.port_map.port_a[5:])
        to_sw = link_map.port_map.dp_z
        to_port = int(link_map.port_map.port_z[5:])

        return from_sw, from_port, to_sw, to_port

    def _get_access_switch(self, mac):
        """Get access switch and port for a given MAC"""
        learned_switches = self.learned_macs.get(mac, {}).get(MAC_LEARNING_SWITCH)

        for switch, switch_map in learned_switches.items():
            port = switch_map[MAC_LEARNING_PORT]
            port_attr = self._get_port_attributes(switch, port)
            if port_attr.get('type') == 'access':
                return switch, port
        return None, None

    def update_radius_result(self, mac, access, segment=None, role=None):
        """Update RADIUS result information for learned host"""
        host_radius = {}
        host_radius[MAC_RADIUS_ACCESS] = access
        host_radius[MAC_RADIUS_SEGMENT] = segment
        host_radius[MAC_RADIUS_ROLE] = role
        self.radius_results[mac] = host_radius

        learned_host = self.learned_macs.get(mac)
        if not learned_host:
            # This covers the case where we do a RADIUS request for a static placement
            self._logger.warning(
                '%s is not a learned mac. Skipping faucet_state_collector update.', mac)
        else:
            learned_host[MAC_RADIUS_RESULT] = host_radius

    @_pre_check()
    def get_host_summary(self):
        """Get a summary of the learned hosts"""
        with self.lock:
            num_hosts = 0
            for mac in self.learned_macs:
                switch, port = self._get_access_switch(mac)
                if switch and port:
                    num_hosts += 1
        return self._make_summary(State.healthy, f'{num_hosts} learned host MACs')

    @_pre_check()
    def get_list_hosts(self, url_base, src_mac):
        """Get access devices"""
        host_macs = {}
        if src_mac and src_mac not in self.learned_macs:
            error_msg = 'MAC address cannot be found. Please use list_hosts to get a list of hosts'
            return self._make_summary(State.broken, error_msg)
        for mac, mac_state in self.learned_macs.items():
            if src_mac and mac == src_mac:
                continue
            switch, port = self._get_access_switch(mac)
            if not switch or not port:
                continue
            mac_deets = host_macs.setdefault(mac, {})
            mac_deets['switch'] = switch
            mac_deets['port'] = port
            mac_deets['host_ips'] = list(mac_state.get(MAC_LEARNING_IP, []))

            metrics = self._get_gauge_metrics()
            self._fill_port_behavior(switch, port, mac_deets, metrics)

            if MAC_RADIUS_RESULT in mac_state:
                mac_deets[MAC_RADIUS_RESULT] = mac_state[MAC_RADIUS_RESULT]

            if src_mac:
                url = f"{url_base}/?host_path?eth_src={src_mac}&eth_dst={mac}"
            else:
                url = f"{url_base}/?list_hosts?eth_src={mac}"
            mac_deets['url'] = url

        key = 'eth_dsts' if src_mac else 'eth_srcs'
        egress_url = f"{url_base}?host_path?eth_src={src_mac}&to_egress=true" if src_mac else None

        return dict_proto({
            key: host_macs,
            'egress_url': egress_url,
        }, HostList)

    def _get_port_attributes(self, switch, port):
        """Get the attributes of a port: description, type, peer_switch, peer_port"""
        cfg_switch = self._get_switch_config(switch)
        ret_attr = {}
        port = int(port)
        if port in cfg_switch.interfaces:
            port_info = cfg_switch.interfaces[port]
            assert port_info, 'missing port_info'
            ret_attr['description'] = port_info.get('description')
            if 'stack' in port_info:
                ret_attr['type'] = 'stack'
                ret_attr['peer_switch'] = port_info['stack']['dp']
                ret_attr['peer_port'] = port_info['stack']['port']
                return ret_attr

            if 'lacp' in port_info:
                ret_attr['type'] = 'egress'
                return ret_attr

            sequester_port_desc = self._config.orchestration.sequester_config.port_description
            if sequester_port_desc and sequester_port_desc == port_info.get('description'):
                ret_attr['type'] = 'sequester'
                return ret_attr

            ret_attr['type'] = 'access'
            return ret_attr

        for port_range, port_info in cfg_switch.interface_ranges.items():
            start_port = int(port_range.split('-')[0])
            end_port = int(port_range.split('-')[1])
            if start_port <= int(port) <= end_port:
                ret_attr['description'] = port_info.get('description')
                ret_attr['type'] = 'access'
                return ret_attr
        raise Exception(f'No valid port classificaiton for {switch}:{port}')

    def _get_egress_port(self, switch):
        """Get egress port of a switch"""
        for port in self.switch_states[switch].get(PORTS, {}):
            port_attr = self._get_port_attributes(switch, port)
            if port_attr.get('type') == 'egress':
                return port
        return None

    def _is_egress_port(self, switch, port):
        port_attr = self._get_port_attributes(switch, port)
        if not port_attr:
            return False
        port_type = port_attr['type']
        return port_type == 'egress'

    def set_placement_callback(self, callback):
        """register callback method to call to process placement info"""
        self._placement_callback = callback

    def set_get_gauge_metrics(self, func):
        """Set get_gauge_metrics method"""
        self._get_gauge_metrics = func

    def set_get_dva_state(self, func):
        """set get_dva_states method"""
        self._get_dva_state = func

    def set_forch_metrics(self, forch_metrics):
        """set object that handles forch varz metrics exposure"""
        self._forch_metrics = forch_metrics

    def set_device_state_reporter(self, device_state_reporter):
        """set object that processes and reports device related states"""
        self._device_state_reporter = device_state_reporter

    def _get_lacp_link_state(self, lacp_role, lacp_state):
        """Return forch link state for given  faucet lacp role and state"""
        if lacp_role == LacpRole.unselected:
            if lacp_state in (LacpState.noact, LacpState.active):
                return STATE_UP
            return STATE_DOWN
        if lacp_role == LacpRole.selected:
            if lacp_state != LacpState.active:
                return STATE_DOWN
            return STATE_ACTIVE
        return STATE_DOWN
