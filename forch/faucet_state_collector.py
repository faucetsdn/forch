"""Processing faucet events"""

import copy
from datetime import datetime
import json
import logging
from threading import RLock

LOGGER = logging.getLogger('fstate')

def dump_states(func):
    """Decorator to dump the current states after the states map is modified"""

    def _set_default(obj):
        if isinstance(obj, set):
            return list(obj)
        return obj

    def wrapped(self, *args, **kwargs):
        res = func(self, *args, **kwargs)
        with self.lock:
            LOGGER.debug(json.dumps(self.system_states, default=_set_default))
        return res

    return wrapped


KEY_SWITCH = "dpids"
KEY_DP_ID = "dp_id"
KEY_PORTS = "ports"
KEY_PORT_STATUS_COUNT = "change_count"
KEY_PORT_STATUS_TS = "timestamp"
KEY_PORT_STATUS_UP = "status_up"
KEY_LEARNED_MACS = "learned_macs"
KEY_MAC_LEARNING_SWITCH = "switches"
KEY_MAC_LEARNING_PORT = "port"
KEY_MAC_LEARNING_IP = "ip_address"
KEY_MAC_LEARNING_TS = "timestamp"
KEY_CONFIG_CHANGE_COUNT = "config_change_count"
SW_STATE = "switch_state"
SW_STATE_CH_TS = "switch_state_last_change"
SW_STATE_CH_COUNT = "switch_state_change_count"
KEY_CONFIG_CHANGE_TYPE = "config_change_type"
KEY_CONFIG_CHANGE_TS = "config_change_timestamp"
TOPOLOGY_ENTRY = "topology"
TOPOLOGY_GRAPH = "graph_obj"
TOPOLOGY_DPS = "dps"
TOPOLOGY_CHANGE_COUNT = "change_count"
TOPOLOGY_HEALTH = "is_healthy"
TOPOLOGY_NOT_HEALTH = "is_wounded"
TOPOLOGY_DP_MAP = "switches"
TOPOLOGY_LINK_MAP = "stack_links"
TOPOLOGY_ROOT = "active_root"
DPS_CFG = "dps_config"
DPS_CFG_CHANGE_COUNT = "config_change_count"
DPS_CFG_CHANGE_TS = "config_change_timestamp"
FAUCET_CONFIG = "faucet_config"
EGRESS_PORT = "port"
EGRESS_TS = "timestamp"
EGRESS_STATE = "egress_state"
EGRESS_LAST_CHG = "egress_state_last_change"
EGRESS_CHANGE_COUNT = "egress_state_change_count"

class FaucetStateCollector:
    """Processing faucet events and store states in the map"""
    def __init__(self):
        self.system_states = \
                {KEY_SWITCH: {}, TOPOLOGY_ENTRY: {}, KEY_LEARNED_MACS: {}, FAUCET_CONFIG: {}}
        self.switch_states = self.system_states[KEY_SWITCH]
        self.topo_state = self.system_states[TOPOLOGY_ENTRY]
        self.lock = RLock()
        self.learned_macs = self.system_states[KEY_LEARNED_MACS]

    def get_system(self):
        """get the system states"""
        return self.system_states

    def get_dataplane_summary(self):
        """Get summary of dataplane"""
        return {
            'state': 'broken',
            'detail': 'not implemented',
            'change_count': 1
        }

    def get_dataplane_state(self):
        """get the topology state"""
        dplane_map = {}
        dplane_map[TOPOLOGY_DP_MAP] = self._get_switch_map()
        dplane_map[TOPOLOGY_LINK_MAP] = self._get_stack_topo()
        self._fill_egress_state(dplane_map)
        return dplane_map

    def get_switch_summary(self):
        """Get summary of switch state"""
        return {
            'state': 'broken',
            'detail': 'not implemented',
            'change_count': 1
        }

    def get_switch_state(self):
        """get a set of all switches"""
        switch_data = {}
        for switch_name in self.switch_states:
            switch_data[switch_name] = self._get_switch(switch_name)
        return {
            'switches_state': 'monkey',
            'switches_state_change_count': 1,
            'switches_state_last_change': "2019-10-11T15:23:21.382479",
            'switches': switch_data
        }

    def _fill_egress_state(self, dplane_map):
        """Return egress state obj"""
        with self.lock:
            egress_obj = self.topo_state.get(EGRESS_STATE, {})
            dplane_map[EGRESS_STATE] = egress_obj.get(EGRESS_STATE)
            dplane_map[EGRESS_LAST_CHG] = egress_obj.get(EGRESS_TS)
            dplane_map[EGRESS_CHANGE_COUNT] = egress_obj.get(EGRESS_CHANGE_COUNT)

    def _get_switch_map(self):
        """returns switch map for topology overview"""
        switch_map = {}
        with self.lock:
            for switch, switch_state in self.switch_states.items():
                switch_map[switch] = {}
                switch_map[switch]["status"] = switch_state.get(SW_STATE, "")
        return switch_map

    def _get_switch(self, switch_name):
        """lock protect get_switch_raw"""
        with self.lock:
            switches = self._get_switch_raw(switch_name)
        return switches

    def _get_switch_raw(self, switch_name):
        """get switches state"""
        switch_map = {}
        # filling switch attributes
        switch_states = self.switch_states.get(str(switch_name), {})
        attributes_map = switch_map.setdefault("attributes", {})
        attributes_map["name"] = switch_name
        attributes_map["dp_id"] = switch_states.get(KEY_DP_ID, "")
        attributes_map["description"] = None

        # filling switch dynamics
        switch_map["config_change_count"] = switch_states.get(KEY_CONFIG_CHANGE_COUNT, "")
        switch_map["config_change_type"] = switch_states.get(KEY_CONFIG_CHANGE_TYPE, "")
        switch_map["config_change_timestamp"] = switch_states.get(KEY_CONFIG_CHANGE_TS, "")

        switch_map[SW_STATE] = switch_states.get(SW_STATE, "")
        switch_map[SW_STATE_CH_TS] = switch_states.get(SW_STATE_CH_TS, "")
        switch_map[SW_STATE_CH_COUNT] = switch_states.get(SW_STATE_CH_COUNT, "")

        switch_port_map = switch_map.setdefault("ports", {})

        # filling port information
        for port_id, port_states in switch_states.get(KEY_PORTS, {}).items():
            port_map = switch_port_map.setdefault(port_id, {})
            # port attributes
            port_attr = self._get_port_attributes(switch_name, port_id)
            switch_port_attributes_map = port_map.setdefault("attributes", {})
            switch_port_attributes_map["description"] = port_attr.get('description', None)
            switch_port_attributes_map["port_type"] = port_attr.get('type', None)
            switch_port_attributes_map["stack_peer_switch"] = port_attr.get('peer_switch', None)
            switch_port_attributes_map["stack_peer_port"] = port_attr.get('peer_port', None)

            # port dynamics
            port_map["status_up"] = port_states.get(KEY_PORT_STATUS_UP, "")
            port_map["status_timestamp"] = port_states.get(KEY_PORT_STATUS_TS, "")
            port_map["status_count"] = port_states.get(KEY_PORT_STATUS_COUNT, "")
            port_map["packet_count"] = None

        self._fill_learned_macs(switch_name, switch_map)
        self._fill_path_to_root(switch_name, switch_map)

        return switch_map

    def _fill_learned_macs(self, switch_name, switch_map):
        """fills learned macs"""
        switch_states = self.switch_states.get(str(switch_name), {})
        for mac in switch_states.get(KEY_LEARNED_MACS, set()):
            mac_states = self.learned_macs.get(mac, {})
            learned_switch = mac_states.get(KEY_MAC_LEARNING_SWITCH, {}).get(switch_name, {})
            learned_port = learned_switch.get(KEY_MAC_LEARNING_PORT, None)
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
            mac_map["ip_address"] = mac_states.get(KEY_MAC_LEARNING_IP, None)
            mac_map["port"] = learned_port
            mac_map["timestamp"] = learned_switch.get(KEY_MAC_LEARNING_TS, None)

    def _fill_path_to_root(self, switch_name, switch_map):
        """populate path to root for switch_state"""
        switch_map["root_path"] = self.get_switch_egress_path(switch_name)['path']

    def _get_stack_topo(self):
        """Returns formatted topology object"""
        topo_map = {}
        with self.lock:
            config_obj = self.system_states.get(FAUCET_CONFIG, {}).get(DPS_CFG, {})
            dps = self.topo_state.get(TOPOLOGY_DPS, {})
            for start_dp, dp_obj in config_obj.items():
                for start_port, iface_obj in dp_obj.get("interfaces", {}).items():
                    peer_dp = iface_obj.get("stack", {}).get("dp")
                    peer_port = str(iface_obj.get("stack", {}).get("port"))
                    if peer_dp and peer_port:
                        link_obj = {}
                        subkey1 = start_dp+":"+start_port
                        subkey2 = peer_dp+":"+peer_port
                        keep_order = subkey1 < subkey2
                        key = subkey1+"-"+subkey2 if keep_order else subkey2+"-"+subkey1
                        link_obj["switch_a"] = start_dp if keep_order else peer_dp
                        link_obj["switch_b"] = peer_dp if keep_order else start_dp
                        link_obj["port_a"] = start_port if keep_order else peer_port
                        link_obj["port_b"] = peer_port if keep_order else start_port
                        if key in topo_map:
                            continue
                        topo_map[key] = link_obj
                        if (dps.get(start_dp)['root_hop_port'] == int(start_port) or
                                dps.get(peer_dp)['root_hop_port'] == int(peer_port)):
                            link_obj["status"] = "ACTIVE"
                        elif self._is_link_up(key):
                            link_obj["status"] = "UP"
                        else:
                            link_obj["status"] = "DOWN"

        return topo_map

    def _is_link_up(self, key):
        """iterates through links in graph obj and returns if link with key is in graph"""
        with self.lock:
            links = self.topo_state.get(TOPOLOGY_GRAPH, {}).get("links", [])
            for link in links:
                if link["key"] == key:
                    return True
        return False

    def _is_port_up(self, switch, port):
        """Check if port is up"""
        with self.lock:
            return self.switch_states.get(str(switch), {})\
                    .get(KEY_PORTS, {}).get(port, {}).get('status_up', False)

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
            link_list = self.topo_state.get(TOPOLOGY_GRAPH).get('links', [])
            dps = self.topo_state.get(TOPOLOGY_DPS, {})
            hop = {'switch': src_switch}
            if src_port:
                hop['in'] = src_port
            while hop:
                next_hop = {}
                egress_port = dps.get(hop['switch'])['root_hop_port']
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
                    res['path'].append(hop)
                    break
                hop = next_hop
        return res

    def get_host_path(self, src_mac, dst_mac=None):
        """Given two MAC addresses in the core network, find the active path between them"""
        res = {'src_ip': None, 'dst_ip': None, 'path': []}
        if not dst_mac:
            return self.get_active_egress_path(src_mac)
        if src_mac not in self.learned_macs or dst_mac not in self.learned_macs:
            return res

        res['src_ip'] = self.learned_macs[src_mac].get(KEY_MAC_LEARNING_IP, None)
        res['dst_ip'] = self.learned_macs[dst_mac].get(KEY_MAC_LEARNING_IP, None)

        src_learned_switches = self.learned_macs[src_mac].get(KEY_MAC_LEARNING_SWITCH, {})
        dst_learned_switches = self.learned_macs[dst_mac].get(KEY_MAC_LEARNING_SWITCH, {})

        next_hops = self._get_graph(src_mac, dst_mac)

        if not next_hops:
            return res

        src_switch, src_port = self._get_access_switch(src_mac)

        next_hop = {'switch': src_switch, 'in': src_port, 'out': None}

        while next_hop['switch'] in next_hops:
            next_hop['out'] = dst_learned_switches[next_hop['switch']][KEY_MAC_LEARNING_PORT]
            res['path'].append(copy.copy(next_hop))
            next_hop['switch'] = next_hops[next_hop['switch']]
            next_hop['in'] = src_learned_switches[next_hop['switch']][KEY_MAC_LEARNING_PORT]

        next_hop['out'] = dst_learned_switches[next_hop['switch']][KEY_MAC_LEARNING_PORT]
        res['path'].append(copy.copy(next_hop))

        return res

    @dump_states
    def process_port_state(self, timestamp, name, port, status):
        """process port state event"""
        with self.lock:
            port_table = self.switch_states\
                .setdefault(name, {})\
                .setdefault(KEY_PORTS, {})\
                .setdefault(port, {})

            port_table[KEY_PORT_STATUS_UP] = status
            port_table[KEY_PORT_STATUS_TS] = datetime.fromtimestamp(timestamp).isoformat()

            port_table[KEY_PORT_STATUS_COUNT] = port_table.setdefault(KEY_PORT_STATUS_COUNT, 0) + 1

    @dump_states
    def process_lag_state(self, timestamp, name, port, status):
        """process lag change event"""
        topo_state = self.topo_state
        with self.lock:
            egress_table = topo_state.setdefault(EGRESS_STATE, {})
            if status or name == egress_table.get(EGRESS_STATE):
                egress_table[EGRESS_STATE] = name if status else "DOWN"
                egress_table[EGRESS_PORT] = port if status else None
                egress_table[EGRESS_TS] = datetime.fromtimestamp(timestamp).isoformat()
                egress_table[EGRESS_CHANGE_COUNT] = egress_table.get(EGRESS_CHANGE_COUNT, 0) + 1

    @dump_states
    # pylint: disable=too-many-arguments
    def process_port_learn(self, timestamp, name, port, mac, src_ip):
        """process port learn event"""
        with self.lock:
            # update global mac table
            global_mac_table = self.learned_macs.setdefault(mac, {})

            global_mac_table[KEY_MAC_LEARNING_IP] = src_ip

            global_mac_switch_table = global_mac_table.setdefault(KEY_MAC_LEARNING_SWITCH, {})
            learning_switch = global_mac_switch_table.setdefault(name, {})
            learning_switch[KEY_MAC_LEARNING_PORT] = port
            learning_switch[KEY_MAC_LEARNING_TS] = datetime.fromtimestamp(timestamp).isoformat()

            # update per switch mac table
            self.switch_states\
                .setdefault(name, {})\
                .setdefault(KEY_LEARNED_MACS, set())\
                .add(mac)

    @dump_states
    def process_dp_config_change(self, timestamp, dp_name, restart_type, dp_id):
        """process config change event"""
        with self.lock:
            # No dp_id (or 0) indicates that this is system-wide, not for a given switch.
            if not dp_id:
                return

            dp_state = self.switch_states.setdefault(dp_name, {})

            dp_state[KEY_DP_ID] = dp_id
            dp_state[KEY_CONFIG_CHANGE_TYPE] = restart_type
            dp_state[KEY_CONFIG_CHANGE_TS] = datetime.fromtimestamp(timestamp).isoformat()
            dp_state[KEY_CONFIG_CHANGE_COUNT] = dp_state.setdefault(KEY_CONFIG_CHANGE_COUNT, 0) + 1

    @dump_states
    def process_dp_change(self, timestamp, dp_name, connected):
        """process dp_change to get dp status"""
        with self.lock:
            if not dp_name:
                return
            dp_state = self.switch_states.setdefault(dp_name, {})
            #TODO: figure out distinction b/w HEALTHY and DAMAGED to replace placeholder "CONNECTED"
            state = "CONNECTED" if connected else "DOWN"
            if dp_state.get(SW_STATE, "") != state:
                dp_state[SW_STATE] = state
                dp_state[SW_STATE_CH_TS] = datetime.fromtimestamp(timestamp).isoformat()
                dp_state[SW_STATE_CH_COUNT] = dp_state.get(SW_STATE_CH_COUNT, 0) + 1

    @dump_states
    def process_dataplane_config_change(self, timestamp, dps_config):
        """Handle config data sent through event channel """
        with self.lock:
            cfg_state = self.system_states[FAUCET_CONFIG]
            cfg_state[DPS_CFG] = dps_config
            cfg_state[DPS_CFG_CHANGE_TS] = datetime.fromtimestamp(timestamp).isoformat()
            cfg_state[DPS_CFG_CHANGE_COUNT] = cfg_state.setdefault(DPS_CFG_CHANGE_COUNT, 0) + 1

    @dump_states
    def process_stack_topo_change(self, timestamp, stack_root, graph, dps):
        """Process stack topology change event"""
        topo_state = self.topo_state
        with self.lock:
            topo_state[TOPOLOGY_ROOT] = stack_root
            topo_state[TOPOLOGY_GRAPH] = graph
            topo_state[TOPOLOGY_DPS] = dps
            topo_state[TOPOLOGY_CHANGE_COUNT] = topo_state.setdefault(TOPOLOGY_CHANGE_COUNT, 0) + 1

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
        src_learned_switches = self.learned_macs[src_mac][KEY_MAC_LEARNING_SWITCH]
        dst_learned_switches = self.learned_macs[dst_mac][KEY_MAC_LEARNING_SWITCH]
        src_learned_port = src_learned_switches.get(sw_1, {}).get(KEY_MAC_LEARNING_PORT, "")
        dst_learned_port = dst_learned_switches.get(sw_2, {}).get(KEY_MAC_LEARNING_PORT, "")

        if src_learned_port == port_1 and dst_learned_port == port_2:
            graph[sw_2] = sw_1

    def _get_access_switch(self, mac):
        """Get access switch and port for a given MAC"""
        learned_switches = self.learned_macs.get(mac, {}).get(KEY_MAC_LEARNING_SWITCH)

        for switch, port_map in learned_switches.items():
            port = port_map[KEY_MAC_LEARNING_PORT]
            port_attr = self._get_port_attributes(switch, port)
            if port_attr['type'] == 'access':
                return switch, port
        return None, None

    def _get_graph(self, src_mac, dst_mac):
        """Get a graph consists of links only used by src and dst MAC"""
        graph = {}
        for link_map in self.topo_state.get(TOPOLOGY_GRAPH, {}).get("links", []):
            if not link_map:
                continue
            sw_1, p_1, sw_2, p_2 = FaucetStateCollector.get_endpoints_from_link(link_map)
            self._add_link(src_mac, dst_mac, sw_1, p_1, sw_2, p_2, graph)
            self._add_link(src_mac, dst_mac, sw_2, p_2, sw_1, p_1, graph)

        return graph

    def _get_port_attributes(self, switch, port):
        """Get the attributes of a port: description, type, peer_switch, peer_port"""
        ret_attr = {}
        cfg_switch = self.system_states.get(FAUCET_CONFIG, {}).get(DPS_CFG, {}).get(switch, None)
        if not cfg_switch:
            return ret_attr

        port = str(port)
        if port in cfg_switch.get('interfaces', {}):
            port_map = cfg_switch['interfaces'][port]
            ret_attr['description'] = port_map.get('description', None)
            if 'stack' in port_map:
                ret_attr['type'] = 'stack'
                ret_attr['peer_switch'] = port_map['stack']['dp']
                ret_attr['peer_port'] = port_map['stack']['port']
            elif 'loop_protect_external' in port_map:
                ret_attr['type'] = 'egress'

            return ret_attr

        for port_range, port_map in cfg_switch.get('interface_ranges', {}).items():
            start_port = int(port_range.split('-')[0])
            end_port = int(port_range.split('-')[1])
            if start_port <= int(port) <= end_port:
                ret_attr['description'] = port_map.get('description', None)
                ret_attr['type'] = 'access'
                return ret_attr

        return ret_attr
