"""Processing faucet events"""

import copy
from datetime import datetime
import json
import logging
import time
import threading
from threading import RLock

from forch.constants import \
    STATE_INACTIVE, STATE_HEALTHY, STATE_UP, STATE_INITIALIZING, \
    STATE_BROKEN, STATE_DOWN, STATE_ACTIVE

LOGGER = logging.getLogger('fstate')


def _dump_states(func):
    """Decorator to dump the current states after the states map is modified"""

    def _set_default(obj):
        if isinstance(obj, set):
            return list(obj)
        return obj

    def wrapped(self, *args, **kwargs):
        res = func(self, *args, **kwargs)
        with self.lock:
            LOGGER.debug(json.dumps(self.switch_states, default=_set_default))
        return res

    return wrapped


_RESTORE_METHODS = {'port': {}, 'dp': {}}

FAUCET_LACP_STATE_UP = 3
FAUCET_STACK_STATE_BAD = 2
FAUCET_STACK_STATE_UP = 3
SWITCH_CONNECTED = "CONNECTED"
SWITCH_DOWN = "DOWN"

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
CONFIG_CHANGE_COUNT = "config_change_count"
SW_STATE = "switch_state"
SW_STATE_LAST_CHANGE = "switch_state_last_change"
SW_STATE_CHANGE_COUNT = "switch_state_change_count"
CONFIG_CHANGE_TYPE = "config_change_type"
CONFIG_CHANGE_TS = "config_change_timestamp"
LINK_STATE = "link_state"
TOPOLOGY_ENTRY = "topology"
TOPOLOGY_DPS = "dps"
TOPOLOGY_CHANGE_COUNT = "topology_change_count"
TOPOLOGY_LAST_CHANGE = "topology_last_change"
LINKS_STATE = "links_state"
LINKS_GRAPH = "links_graph"
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
EGRESS_LAST_UPDATE = "egress_state_last_update"
EGRESS_CHANGE_COUNT = "egress_state_change_count"


# pylint: disable=too-many-public-methods
class FaucetStateCollector:
    """Processing faucet events and store states in the map"""
    def __init__(self):
        self.switch_states = {}
        self.topo_state = {}
        self.topo_state.setdefault(LINKS_GRAPH, [])
        self.learned_macs = {}
        self.faucet_config = {}
        self.lock = RLock()
        self._lock = threading.Lock()
        self.process_lag_state(time.time(), None, None, False)
        self._is_active = False
        self._is_connected = False

    def set_active(self, is_active):
        """Set active state"""
        with self._lock:
            self._is_active = is_active

    def set_connected(self, is_connected):
        """Set active state"""
        with self._lock:
            self._is_connected = is_connected

    # pylint: disable=no-self-argument, protected-access
    def _pre_check(state_name):
        def pre_check(func):
            def wrapped(self, *args, **kwargs):
                with self._lock:
                    if not self._is_active:
                        detail = 'This controller is inactive. Please view peer controller.'
                        return {state_name: STATE_INACTIVE, 'detail': detail}
                    if not self._is_connected:
                        detail = 'Diconnected from Faucet event socket.'
                        return {state_name: STATE_BROKEN, 'detail': detail}
                return func(self, *args, **kwargs)
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
        current_time = time.time()
        for label_name, method_map in _RESTORE_METHODS.items():
            for metric_name, restore_method in method_map.items():
                if metric_name not in metrics:
                    LOGGER.warning("Metrics does not contain: %s", metric_name)
                    continue
                for sample in metrics[metric_name].samples:
                    switch = sample.labels['dp_name']
                    label = int(sample.labels.get(label_name, 0))
                    restore_method(self, current_time, switch, label, sample.value)
        return int(metrics['faucet_event_id'].samples[0].value)

    @_pre_check(state_name='state')
    def get_dataplane_summary(self):
        """Get summary of dataplane"""
        dplane_state = self._get_dataplane_state()
        return {
            'state': dplane_state.get('dataplane_state'),
            'detail': dplane_state.get('dataplane_state_detail'),
            'change_count': dplane_state.get('dataplane_state_change_count'),
            'last_change': dplane_state.get('dataplane_state_last_change')
        }

    def _update_dataplane_detail(self, dplane_state):
        detail = []
        state = STATE_INITIALIZING

        egress = dplane_state.get('egress', {})
        egress_state = egress.get(EGRESS_STATE)
        egress_detail = egress.get(EGRESS_DETAIL)

        if egress:
            state = STATE_HEALTHY if egress_state == STATE_UP else STATE_BROKEN
        if egress_detail:
            detail.append("egress:" + str(egress_detail))

        broken_sw = self._get_broken_switches(dplane_state)
        if broken_sw:
            state = STATE_BROKEN
            detail.append("broken switches: " + str(broken_sw))

        broken_links = self._get_broken_links(dplane_state)
        if broken_links:
            state = STATE_BROKEN
            detail.append("broken links: " + str(broken_links))

        dplane_state['dataplane_state'] = state
        dplane_state['dataplane_state_detail'] = "; ".join(detail)

    @_pre_check(state_name='dataplane_state')
    def get_dataplane_state(self):
        """get the topology state"""
        return self._get_dataplane_state()

    def _get_dataplane_state(self):
        """get the topology state impl"""
        dplane_state = {}
        change_count = 0
        last_change = '#n/a'  # Clevery chosen to be sorted less than timestamp.

        switch_map = self._get_switch_map()
        dplane_state['switch'] = switch_map
        change_count += switch_map.get(SW_STATE_CHANGE_COUNT, 0)
        last_change = max(last_change, switch_map.get(SW_STATE_LAST_CHANGE, ''))

        stack_topo = self._get_stack_topo()
        dplane_state['stack'] = stack_topo
        change_count += stack_topo.get(LINKS_CHANGE_COUNT, 0)
        last_change = max(last_change, stack_topo.get(LINKS_LAST_CHANGE, ''))

        egress_state = dplane_state.setdefault('egress', {})
        self._fill_egress_state(egress_state)
        change_count += egress_state.get(EGRESS_CHANGE_COUNT, 0)
        last_change = max(last_change, egress_state.get(EGRESS_LAST_CHANGE, ''))

        self._update_dataplane_detail(dplane_state)
        dplane_state['dataplane_state_change_count'] = change_count
        dplane_state['dataplane_state_last_change'] = last_change

        return dplane_state

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
        return broken_links

    @_pre_check(state_name='state')
    def get_switch_summary(self):
        """Get summary of switch state"""
        switch_state = self._get_switch_state(None, None)
        return {
            'state': switch_state['switches_state'],
            'detail': switch_state['switches_state_detail'],
            'change_count': switch_state['switches_state_change_count'],
            'last_change': switch_state['switches_state_last_change']
        }

    def _augment_mac_urls(self, url_base, switch_data):
        if url_base:
            for mac, mac_data in switch_data.get('access_port_macs', {}).items():
                mac_data['url'] = f"{url_base}/?list_hosts?eth_src={mac}"

    @_pre_check(state_name='switch_state')
    def get_switch_state(self, switch, port, url_base=None):
        """get a set of all switches"""
        return self._get_switch_state(switch, port, url_base)

    def _get_switch_state(self, switch, port, url_base=None):
        """Get switch state impl"""
        switches_data = {}
        broken = []
        change_count = 0
        last_change = '#n/a'  # Clevery chosen to be sorted less than timestamp.
        for switch_name in self.switch_states:
            switch_data = self._get_switch(switch_name, port)
            switches_data[switch_name] = switch_data
            change_count += switch_data.get(SW_STATE_CHANGE_COUNT, 0)
            last_change = max(last_change, switch_data.get(SW_STATE_LAST_CHANGE, ''))
            if switch_data[SW_STATE] != STATE_ACTIVE:
                broken.append(switch_name)
            self._augment_mac_urls(url_base, switch_data)

        if not self.switch_states:
            switches_state = STATE_BROKEN
            state_detail = 'No switches connected'
        elif broken:
            switches_state = STATE_BROKEN
            state_detail = 'Switches in broken state: ' + ', '.join(broken)
        else:
            switches_state = STATE_HEALTHY
            state_detail = None

        result = {
            'switches_state': switches_state,
            'switches_state_detail': state_detail,
            'switches_state_change_count': change_count,
            'switches_state_last_change': last_change,
            'switches': switches_data
        }

        if switch:
            result['switches'] = {switch: switches_data[switch]}
            result['switches_restrict'] = switch

        return result

    def cleanup(self):
        """Clean up internal data"""
        with self.lock:
            self.learned_macs.clear()
            for switch_data in self.switch_states.values():
                switch_data.get(LEARNED_MACS, set()).clear()

    def _fill_egress_state(self, target_obj):
        """Return egress state obj"""
        with self.lock:
            egress_obj = self.topo_state.get('egress', {})
            target_obj[EGRESS_STATE] = egress_obj.get(EGRESS_STATE)
            target_obj[EGRESS_DETAIL] = egress_obj.get(EGRESS_DETAIL)
            target_obj[EGRESS_LAST_UPDATE] = egress_obj.get(EGRESS_LAST_UPDATE)
            target_obj[EGRESS_LAST_CHANGE] = egress_obj.get(EGRESS_LAST_CHANGE)
            target_obj[EGRESS_CHANGE_COUNT] = egress_obj.get(EGRESS_CHANGE_COUNT)
            target_obj[TOPOLOGY_ROOT] = self.topo_state.get(TOPOLOGY_ROOT)

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

    def _get_switch(self, switch_name, port):
        """lock protect get_switch_raw"""
        with self.lock:
            return self._get_switch_raw(switch_name, port)

    def _get_switch_raw(self, switch_name, port):
        """get switches state"""
        switch_map = {}
        # filling switch attributes
        switch_states = self.switch_states.get(str(switch_name), {})
        attributes_map = switch_map.setdefault("attributes", {})
        attributes_map["dp_id"] = switch_states.get(DP_ID)

        # filling switch dynamics
        switch_map["restart_type_event_count"] = switch_states.get(CONFIG_CHANGE_COUNT)
        switch_map["restart_type"] = switch_states.get(CONFIG_CHANGE_TYPE)
        switch_map["restart_type_last_change"] = switch_states.get(CONFIG_CHANGE_TS)

        if switch_states.get(SW_STATE) == SWITCH_CONNECTED:
            switch_map[SW_STATE] = STATE_ACTIVE
        else:
            switch_map[SW_STATE] = STATE_DOWN
        switch_map[SW_STATE_LAST_CHANGE] = switch_states.get(SW_STATE_LAST_CHANGE, '')
        switch_map[SW_STATE_CHANGE_COUNT] = switch_states.get(SW_STATE_CHANGE_COUNT, 0)

        # filling port information
        switch_port_map = switch_map.setdefault('ports', {})
        if port:
            port = int(port)
            switch_port_map[port] = self._get_port_state(switch_name, port)
            switch_map['ports_restrict'] = port
        else:
            for port_id in switch_states.get(PORTS, {}):
                switch_port_map[port_id] = self._get_port_state(switch_name, port_id)

        self._fill_learned_macs(switch_name, switch_map)
        self._fill_path_to_root(switch_name, switch_map)

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
        switch_port_attributes_map["stack_peer_switch"] = port_attr.get('peer_switch')
        switch_port_attributes_map["stack_peer_port"] = port_attr.get('peer_port')

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
            if port_type == 'access':
                switch_learned_mac_map = switch_map.setdefault('access_port_macs', {})
            elif port_type == 'stack':
                switch_learned_mac_map = switch_map.setdefault('stacking_port_macs', {})
            elif port_type == 'egress':
                switch_learned_mac_map = switch_map.setdefault('egress_port_macs', {})
            else:
                raise Exception('Unknown port type %s' % port_type)

            mac_map = switch_learned_mac_map.setdefault(mac, {})
            mac_map["ip_address"] = mac_states.get(MAC_LEARNING_IP, None)
            mac_map["port"] = learned_port
            mac_map["timestamp"] = learned_switch.get(MAC_LEARNING_TS, None)

    def _fill_path_to_root(self, switch_name, switch_map):
        """populate path to root for switch_state"""
        switch_map["root_path"] = self.get_switch_egress_path(switch_name).get('path')

    @staticmethod
    def _make_key(start_dp, start_port, peer_dp, peer_port):
        subkey1 = start_dp+":"+start_port
        subkey2 = peer_dp+":"+peer_port
        keep_order = subkey1 < subkey2
        return subkey1+"@"+subkey2 if keep_order else subkey2+"@"+subkey1

    def _get_topo_map(self):
        topo_map = {}
        config_obj = self.faucet_config.get(DPS_CFG)
        if not config_obj:
            return None
        for local_dp, dp_obj in config_obj.items():
            for local_port, iface_obj in dp_obj.get("interfaces", {}).items():
                peer_dp = iface_obj.get("stack", {}).get("dp")
                peer_port = str(iface_obj.get("stack", {}).get("port"))
                if peer_dp and peer_port:
                    key = self._make_key(local_dp, local_port, peer_dp, peer_port)
                    if key not in topo_map:
                        link_state = self._get_link_state(local_dp, local_port, peer_dp, peer_port)
                        topo_map.setdefault(key, {})[LINK_STATE] = link_state
        return topo_map

    def _get_link_state(self, local_dp, local_port, peer_dp, peer_port):
        dps = self.topo_state.get(TOPOLOGY_DPS, {})
        if (dps.get(local_dp, {}).get('root_hop_port') == int(local_port) or
                dps.get(peer_dp, {}).get('root_hop_port') == int(peer_port)):
            return STATE_ACTIVE
        dp_state = self.topo_state.setdefault(LINKS_STATE, {}).setdefault(local_dp, {})
        port_state = dp_state.setdefault(int(local_port), {}).get('state')
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
                return None
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
        res = {'path': []}
        if src_mac not in self.learned_macs:
            return res
        src_switch, src_port = self._get_access_switch(src_mac)
        if not src_switch or not src_port:
            return res
        return self.get_switch_egress_path(src_switch, src_port)

    def get_switch_egress_path(self, src_switch, src_port=None):
        """"Returns path to egress from given switch. Appends ingress port to first hop if given"""
        res = {'path': []}
        with self.lock:
            link_list = self.topo_state.get(LINKS_GRAPH)
            dps = self.topo_state.get(TOPOLOGY_DPS, {})
            if not dps or not link_list:
                return {
                    'state': STATE_BROKEN,
                    'error': 'Missing state data'
                }
            hop = {'switch': src_switch}
            if src_port:
                hop['in'] = src_port
            while hop:
                next_hop = {}
                egress_port = dps.get(hop['switch'], {}).get('root_hop_port')
                if egress_port:
                    hop['out'] = egress_port
                    for link_map in link_list:
                        if not link_map:
                            continue
                        sw_1, port_1, sw_2, port_2 = \
                                FaucetStateCollector.get_endpoints_from_link(link_map)
                        if hop['switch'] == sw_1 and egress_port == port_1:
                            next_hop['switch'] = sw_2
                            next_hop['in'] = port_2
                            break
                        if hop['switch'] == sw_2 and egress_port == port_2:
                            next_hop['switch'] = sw_1
                            next_hop['in'] = port_1
                            break
                    res['path'].append(hop)
                elif hop['switch'] == self.topo_state.get(TOPOLOGY_ROOT):
                    hop['egress'] = self._get_egress_port(hop['switch'])
                    res['path'].append(hop)
                    break
                hop = next_hop
        return res

    @_pre_check(state_name='host_path_state')
    def get_host_path(self, src_mac, dst_mac, to_egress):
        """Given two MAC addresses in the core network, find the active path between them"""
        if not src_mac:
            return {'error': 'Empty eth_src. Please use list_hosts to get a list of hosts'}
        if not dst_mac and not to_egress:
            return {'error': 'Empty eth_dst. Use list_hosts, or set to_egress=true'}

        if src_mac not in self.learned_macs or dst_mac and dst_mac not in self.learned_macs:
            error_msg = 'MAC address cannot be found. Please use list_hosts to get a list of hosts'
            return {'error': error_msg}

        if to_egress:
            ret_map = self.get_active_egress_path(src_mac)
            src_ip = self.learned_macs.get(src_mac, {}).get(MAC_LEARNING_IP)
            ret_map['src_ip'] = src_ip
            return ret_map

        res = {'src_ip': self.learned_macs[src_mac].get(MAC_LEARNING_IP),
               'dst_ip': self.learned_macs[dst_mac].get(MAC_LEARNING_IP),
               'path': []}

        src_learned_switches = self.learned_macs[src_mac].get(MAC_LEARNING_SWITCH, {})
        dst_learned_switches = self.learned_macs[dst_mac].get(MAC_LEARNING_SWITCH, {})

        next_hops = self._get_graph(src_mac, dst_mac)

        if not next_hops:
            return res

        src_switch, src_port = self._get_access_switch(src_mac)

        next_hop = {'switch': src_switch, 'in': src_port, 'out': None}

        while next_hop['switch'] in next_hops:
            next_hop['out'] = dst_learned_switches[next_hop['switch']][MAC_LEARNING_PORT]
            res['path'].append(copy.copy(next_hop))
            next_hop['switch'] = next_hops[next_hop['switch']]
            next_hop['in'] = src_learned_switches[next_hop['switch']][MAC_LEARNING_PORT]

        next_hop['out'] = dst_learned_switches[next_hop['switch']][MAC_LEARNING_PORT]
        res['path'].append(copy.copy(next_hop))

        return res

    @_dump_states
    @_register_restore_state_method(label_name='port', metric_name='port_status')
    def process_port_state(self, timestamp, name, port, state):
        """process port state event"""
        with self.lock:
            port_table = self.switch_states\
                .setdefault(name, {})\
                .setdefault(PORTS, {})\
                .setdefault(port, {})

            port_table[PORT_STATE_UP] = state
            port_table[PORT_STATE_TS] = datetime.fromtimestamp(timestamp).isoformat()
            port_table[PORT_STATE_COUNT] = port_table.setdefault(PORT_STATE_COUNT, 0) + 1

    @_dump_states
    @_register_restore_state_method(label_name='port', metric_name='port_lacp_state')
    def process_lag_state(self, timestamp, name, port, lacp_state):
        """process lag change event"""
        with self.lock:
            egress_state = self.topo_state.setdefault('egress', {})
            old_egress_name = egress_state.get(EGRESS_DETAIL)
            lacp_up = lacp_state == FAUCET_LACP_STATE_UP
            if old_egress_name and old_egress_name != name and not lacp_up:
                return

            egress_state[EGRESS_LAST_UPDATE] = datetime.fromtimestamp(timestamp).isoformat()
            old_state = egress_state.get(EGRESS_STATE)
            new_state = STATE_UP if lacp_up else STATE_DOWN
            if new_state != old_state:
                change_count = egress_state.get(EGRESS_CHANGE_COUNT, 0) + 1
                LOGGER.info('lag_state #%d %s, %s -> %s', change_count, name, old_state, new_state)
                egress_state[EGRESS_STATE] = new_state
                egress_state[EGRESS_DETAIL] = name if lacp_up else None
                egress_state[EGRESS_LAST_CHANGE] = datetime.fromtimestamp(timestamp).isoformat()
                egress_state[EGRESS_CHANGE_COUNT] = change_count

    @_dump_states
    # pylint: disable=too-many-arguments
    def process_port_learn(self, timestamp, name, port, mac, src_ip):
        """process port learn event"""
        with self.lock:
            # update global mac table
            global_mac_table = self.learned_macs.setdefault(mac, {})

            global_mac_table[MAC_LEARNING_IP] = src_ip

            global_mac_switch_table = global_mac_table.setdefault(MAC_LEARNING_SWITCH, {})
            learning_switch = global_mac_switch_table.setdefault(name, {})
            learning_switch[MAC_LEARNING_PORT] = port
            learning_switch[MAC_LEARNING_TS] = datetime.fromtimestamp(timestamp).isoformat()

            # update per switch mac table
            self.switch_states\
                .setdefault(name, {})\
                .setdefault(LEARNED_MACS, set())\
                .add(mac)

    @_dump_states
    def process_dp_config_change(self, timestamp, dp_name, restart_type, dp_id):
        """process config change event"""
        with self.lock:
            # No dp_id (or 0) indicates that this is system-wide, not for a given switch.
            if not dp_id:
                return

            dp_state = self.switch_states.setdefault(dp_name, {})

            change_count = dp_state.get(CONFIG_CHANGE_COUNT, 0) + 1
            LOGGER.info('dp_config #%d %s change type %s', change_count, dp_id, restart_type)
            dp_state[DP_ID] = dp_id
            dp_state[CONFIG_CHANGE_TYPE] = restart_type
            dp_state[CONFIG_CHANGE_TS] = datetime.fromtimestamp(timestamp).isoformat()
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
                LOGGER.info('dp_change #%d %s, %s -> %s', change_count, dp_name,
                            dp_state.get(SW_STATE), new_state)
                dp_state[SW_STATE] = new_state
                dp_state[SW_STATE_LAST_CHANGE] = datetime.fromtimestamp(timestamp).isoformat()
                dp_state[SW_STATE_CHANGE_COUNT] = change_count

    @_dump_states
    def process_dataplane_config_change(self, timestamp, dps_config):
        """Handle config data sent through event channel """
        with self.lock:
            cfg_state = self.faucet_config
            change_count = cfg_state.get(DPS_CFG_CHANGE_COUNT, 0) + 1
            LOGGER.info('dataplane_config #%d change', change_count)
            cfg_state[DPS_CFG] = dps_config
            cfg_state[DPS_CFG_CHANGE_TS] = datetime.fromtimestamp(timestamp).isoformat()
            cfg_state[DPS_CFG_CHANGE_COUNT] = change_count

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
                LOGGER.info('stack_state_links #%d %s:%d is now %s', link_change_count,
                            dp_name, port, new_state)

    @_dump_states
    def process_stack_topo_change(self, timestamp, stack_root, graph, dps):
        """Process stack topology change event"""
        topo_state = self.topo_state
        with self.lock:
            link_graph = graph.get('links')
            if topo_state.get(LINKS_GRAPH) != link_graph:
                topo_state[LINKS_GRAPH] = link_graph
                link_change_count = self._update_stack_links_stats(timestamp)
                graph_links = [link['key'] for link in link_graph]
                graph_links.sort()
                LOGGER.info('stack_topo_links #%d links: %s', link_change_count, graph_links)

            if topo_state.get(TOPOLOGY_ROOT) != stack_root or topo_state.get(TOPOLOGY_DPS) != dps:
                topo_change_count = topo_state.get(TOPOLOGY_CHANGE_COUNT, 0) + 1
                LOGGER.info('stack_topo change #%d to root %s', topo_change_count, stack_root)
                topo_state[TOPOLOGY_ROOT] = stack_root
                topo_state[TOPOLOGY_DPS] = dps
                topo_state[TOPOLOGY_CHANGE_COUNT] = topo_change_count
                topo_state[TOPOLOGY_LAST_CHANGE] = datetime.fromtimestamp(timestamp).isoformat()

    def _update_stack_links_stats(self, timestamp):
        link_change_count = self.topo_state.get(LINKS_CHANGE_COUNT, 0) + 1
        self.topo_state[LINKS_CHANGE_COUNT] = link_change_count
        self.topo_state[LINKS_LAST_CHANGE] = datetime.fromtimestamp(timestamp).isoformat()
        return link_change_count

    @staticmethod
    def get_endpoints_from_link(link_map):
        """Get the the pair of switch and port for a link"""
        from_sw = link_map["port_map"]["dp_a"]
        from_port = int(link_map["port_map"]["port_a"][5:])
        to_sw = link_map["port_map"]["dp_z"]
        to_port = int(link_map["port_map"]["port_z"][5:])

        return from_sw, from_port, to_sw, to_port

    # pylint: disable=too-many-arguments
    def _add_link(self, src_mac, dst_mac, sw_1, port_1, sw_2, port_2, graph):
        """Insert link into graph if link is used by the src and dst"""
        src_learned_switches = self.learned_macs[src_mac][MAC_LEARNING_SWITCH]
        dst_learned_switches = self.learned_macs[dst_mac][MAC_LEARNING_SWITCH]
        src_learned_port = src_learned_switches.get(sw_1, {}).get(MAC_LEARNING_PORT, "")
        dst_learned_port = dst_learned_switches.get(sw_2, {}).get(MAC_LEARNING_PORT, "")

        if src_learned_port == port_1 and dst_learned_port == port_2:
            graph[sw_2] = sw_1

    def _get_access_switch(self, mac):
        """Get access switch and port for a given MAC"""
        learned_switches = self.learned_macs.get(mac, {}).get(MAC_LEARNING_SWITCH)

        for switch, port_map in learned_switches.items():
            port = port_map[MAC_LEARNING_PORT]
            port_attr = self._get_port_attributes(switch, port)
            if port_attr.get('type') == 'access':
                return switch, port
        return None, None

    @_pre_check(state_name='state')
    def get_host_summary(self):
        """Get a summary of the learned hosts"""
        with self.lock:
            num_hosts = len(self.learned_macs)
        return {
            'state': STATE_HEALTHY,
            'detail': f'{num_hosts} learned host MACs'
        }

    @_pre_check(state_name='hosts_list_state')
    def get_list_hosts(self, url_base, src_mac):
        """Get access devices"""
        host_macs = {}
        if src_mac and src_mac not in self.learned_macs:
            error_msg = 'MAC address cannot be found. Please use list_hosts to get a list of hosts'
            return {'error': error_msg}
        for mac, mac_state in self.learned_macs.items():
            if mac == src_mac:
                continue
            switch, port = self._get_access_switch(mac)
            if not switch or not port:
                continue
            mac_deets = host_macs.setdefault(mac, {})
            mac_deets['switch'] = switch
            mac_deets['port'] = port
            mac_deets['host_ip'] = mac_state.get(MAC_LEARNING_IP)

            if src_mac:
                url = f"{url_base}/?host_path?eth_src={src_mac}&eth_dst={mac}"
            else:
                url = f"{url_base}/?list_hosts?eth_src={mac}"
            mac_deets['url'] = url

        key = 'eth_dsts' if src_mac else 'eth_srcs'
        return {key: host_macs}

    def _get_graph(self, src_mac, dst_mac):
        """Get a graph consists of links only used by src and dst MAC"""
        graph = {}
        for link_map in self.topo_state.get(LINKS_GRAPH):
            if not link_map:
                continue
            sw_1, p_1, sw_2, p_2 = FaucetStateCollector.get_endpoints_from_link(link_map)
            self._add_link(src_mac, dst_mac, sw_1, p_1, sw_2, p_2, graph)
            self._add_link(src_mac, dst_mac, sw_2, p_2, sw_1, p_1, graph)

        return graph

    def _get_port_attributes(self, switch, port):
        """Get the attributes of a port: description, type, peer_switch, peer_port"""
        ret_attr = {}
        cfg_switch = self.faucet_config.get(DPS_CFG, {}).get(switch)
        if not cfg_switch:
            return ret_attr

        port = str(port)
        if port in cfg_switch.get('interfaces', {}):
            port_map = cfg_switch['interfaces'][port]
            ret_attr['description'] = port_map.get('description')
            if 'stack' in port_map:
                ret_attr['type'] = 'stack'
                ret_attr['peer_switch'] = port_map['stack']['dp']
                ret_attr['peer_port'] = port_map['stack']['port']
                return ret_attr

            if 'loop_protect_external' in port_map:
                ret_attr['type'] = 'egress'
                return ret_attr

            ret_attr['type'] = 'access'
            return ret_attr

        for port_range, port_map in cfg_switch.get('interface_ranges', {}).items():
            start_port = int(port_range.split('-')[0])
            end_port = int(port_range.split('-')[1])
            if start_port <= int(port) <= end_port:
                ret_attr['description'] = port_map.get('description')
                ret_attr['type'] = 'access'
                return ret_attr

        return ret_attr

    def _get_egress_port(self, switch):
        """Get egress port of a switch"""
        for port in self.switch_states.get(switch, {}).get(PORTS, {}):
            port_attr = self._get_port_attributes(switch, port)
            if port_attr.get('type') == 'egress':
                return port
        return None
