"""Collecting the states of the local system"""

from datetime import datetime
import logging
import os
import re
import signal
import threading
import time

import psutil
import yaml

from forch.proto.process_state_pb2 import ProcessState
from forch.proto.shared_constants_pb2 import State
from forch.proto.system_state_pb2 import StateSummary
from forch.utils import dict_proto

LOGGER = logging.getLogger('lstate')

_PROC_ATTRS = ['cmdline', 'cpu_times', 'memory_info']

class LocalStateCollector:
    """Storing local system states"""

    def __init__(self, config, cleanup_handler, active_state_handler):
        self._state = {'processes': {}, 'vrrp': {}}
        self._process_state = self._state['processes']
        self._process_state['connections'] = {}
        self._vrrp_state = self._state['vrrp']
        self._last_error = {}
        self._current_time = None
        self._conn_state = None
        self._conn_state_count = 0
        self._lock = threading.Lock()

        self._target_procs = config.processes
        self._check_vrrp = config.check_vrrp
        self._connections = config.connections
        self._process_interval = config.scan_interval_sec or 60

        self._cleanup_handler = cleanup_handler
        self._active_state_handler = active_state_handler

        LOGGER.info('Scanning %s processes every %ds',
                    len(self._target_procs), self._process_interval)

    def initialize(self):
        """Initialize LocalStateCollector"""
        if not self._check_vrrp:
            self._vrrp_state['is_master'] = True
            self._active_state_handler(True)

        self.start_process_loop()

    def get_process_summary(self):
        """Return a summary of process table"""
        process_state = self.get_process_state()
        return dict_proto({
            'state': process_state.process_state,
            'detail': process_state.process_state_detail,
            'change_count': process_state.process_state_change_count,
            'last_update': process_state.process_state_last_update,
            'last_change': process_state.process_state_last_change
        }, StateSummary)

    def get_process_state(self):
        """Get the states of processes"""
        with self._lock:
            return dict_proto(self._process_state, ProcessState)

    def _check_process_info(self):
        """Check the raw information of processes"""

        process_state = self._process_state
        process_map = {}
        procs = self._get_target_processes()
        broken = []

        # fill up process info
        for target_name in self._target_procs:
            state_map = process_map.setdefault(target_name, {})
            proc_list = procs.get(target_name, [])
            target_count = self._target_procs[target_name].count or 1
            state, detail = self._extract_process_state(target_name, target_count, proc_list)
            state_map['detail'] = detail
            if state:
                state_map['state'] = State.healthy
                state_map.update(state)
                self._last_error.pop(target_name, None)
                continue
            state_map['state'] = State.broken
            if detail != self._last_error.get(target_name):
                LOGGER.error(detail)
                self._last_error[target_name] = detail
            broken.append(target_name)

        process_state['processes'] = process_map
        process_state['process_state_last_update'] = self._current_time

        old_state = process_state.get('process_state')
        state = State.broken if broken else State.healthy

        old_state_detail = process_state.get('process_state_detail')
        state_detail = 'Processes in broken state: ' + ', '.join(broken) if broken else ''

        if state != old_state or state_detail != old_state_detail:
            state_change_count = process_state.get('process_state_change_count', 0) + 1
            LOGGER.info('process_state #%d is %s: %s', state_change_count, state, state_detail)
            process_state['process_state'] = state
            process_state['process_state_detail'] = state_detail
            process_state['process_state_change_count'] = state_change_count
            process_state['process_state_last_change'] = self._current_time

    def _get_target_processes(self):
        """Get target processes"""
        procs = {}
        for proc in psutil.process_iter(attrs=_PROC_ATTRS):
            cmd_line_str = ' '.join(proc.info['cmdline'])
            for target_name, process_cfg in self._target_procs.items():
                proc_list = procs.setdefault(target_name, [])
                if re.search(process_cfg.regex, cmd_line_str):
                    print(f'{target_name}: {process_cfg.regex}')
                    proc_list.append(proc)

        return procs

    def _extract_process_state(self, proc_name, proc_count, proc_list):
        """Fill process state for a single process"""
        if len(proc_list) != proc_count:
            return None, f"Process {proc_name}: number of process ({len(proc_list)}) " \
                f"does not match target count ({proc_count})"

        old_proc_map = self._process_state.get('processes', {}).get(proc_name, {})
        proc_map = {}

        cmd_line = ' '.join(proc_list[0].info['cmdline']) if len(proc_list) == 1 else 'multiple'
        proc_map['cmd_line'] = cmd_line
        create_time_max = max(proc.create_time() for proc in proc_list)
        create_time = datetime.fromtimestamp(create_time_max).isoformat()
        proc_map['create_time'] = create_time
        proc_map['create_time_last_update'] = self._current_time

        if create_time != old_proc_map.get('create_time'):
            change_count = old_proc_map.get('create_time_change_count', 0) + 1
            LOGGER.info('create_time #%d for %s: %s', change_count, proc_name, create_time)
            proc_map['create_time_change_count'] = change_count
            proc_map['create_time_last_change'] = self._current_time

        error = self._aggregate_process_stats(proc_map, proc_list)

        if error:
            return None, error

        return proc_map, None

    def _aggregate_process_stats(self, proc_map, proc_list):
        cpu_time_user = 0.0
        cpu_time_system = 0.0
        cpu_time_iowait = None
        memory_rss = 0.0
        memory_vms = 0.0

        try:
            for proc in proc_list:
                cpu_time_user += proc.info['cpu_times'].user
                cpu_time_system += proc.info['cpu_times'].system
                if hasattr(proc.info['cpu_times'], 'iowait'):
                    if not cpu_time_iowait:
                        cpu_time_iowait = 0.0
                    cpu_time_iowait += proc.cpu_times().iowait

                memory_rss += proc.info['memory_info'].rss / 1e6
                memory_vms += proc.info['memory_info'].vms / 1e6
        except Exception as e:
            return "Error extracting process info: %s" % e

        proc_map['cpu_times_s'] = {}
        proc_map['cpu_times_s']['user'] = cpu_time_user / len(proc_list)
        proc_map['cpu_times_s']['system'] = cpu_time_system / len(proc_list)
        if cpu_time_iowait:
            proc_map['cpu_times_s']['iowait'] = cpu_time_iowait / len(proc_list)

        proc_map['memory_info_mb'] = {}
        proc_map['memory_info_mb']['rss'] = memory_rss / len(proc_list)
        proc_map['memory_info_mb']['vms'] = memory_vms / len(proc_list)

        return None

    def _check_connections(self):
        connections = self._fetch_connections()
        connection_info = self._process_state['connections']
        connection_info['local_ports'] = {
            str(port): self._extract_conn(connections, port) for port in self._connections
        }
        conn_list = []
        for port_info in connection_info['local_ports'].values():
            for foreign_address in port_info['foreign_addresses']:
                conn_list.append(foreign_address)
        conn_list.sort()
        conn_state = str(conn_list)
        if conn_state != self._conn_state:
            self._conn_state = conn_state
            self._conn_state_count += 1
            LOGGER.info('conn_state #%d: %s', self._conn_state_count, conn_state)
            connection_info['detail'] = conn_state
            connection_info['change_count'] = self._conn_state_count
            connection_info['last_change'] = self._current_time
        connection_info['last_update'] = self._current_time

    def _fetch_connections(self):
        connections = {}
        with os.popen('netstat -npa 2>/dev/null') as lines:
            for line in lines:
                if 'ESTABLISHED' in line:
                    try:
                        parts = line.split()
                        local_address = parts[3]
                        local_parts = local_address.split(':')
                        local_port = int(local_parts[-1])
                        foreign_address = parts[4]
                        connections[foreign_address] = {
                            'local_port': local_port,
                            'process_info': parts[6]
                        }
                    except Exception as e:
                        LOGGER.error('Processing netstat entry: %s', e)

        return connections

    def _extract_conn(self, connections, port):
        foreign_addresses = {}
        process_entry = None
        for foreign_address in connections:
            entry = connections[foreign_address]
            if entry['local_port'] == port:
                new_process_entry = entry['process_info']
                if process_entry and new_process_entry != process_entry:
                    LOGGER.error('Insonsistent process entry for %s: %s != %s',
                                 port, process_entry, new_process_entry)
                process_entry = new_process_entry
                foreign_addresses[foreign_address] = {
                    'established': 'now'
                }
        return {
            'process_entry': process_entry,
            'foreign_addresses': foreign_addresses
        }

    def _check_vrrp_info(self):
        """Get vrrp info"""
        try:
            if not self._check_vrrp:
                return
            with open('/var/run/keepalived.pid') as pid_file:
                pid = int(pid_file.readline())
            os.kill(pid, signal.SIGUSR2)
            time.sleep(1)
            with open('/tmp/keepalived.stats') as stats_file:
                stats_file.readline()
                stats = yaml.safe_load(stats_file)

                self._vrrp_state.update(self._extract_vrrp_state(stats))
                active_state = State.active if self._vrrp_state['is_master'] else State.inactive
                self._active_state_handler(active_state)

        except Exception as e:
            LOGGER.error("Cannot get VRRP info, setting controller to inactive: %s", e)
            self._active_state_handler(State.broken)

    def _extract_vrrp_state(self, stats):
        """Extract vrrp state from keepalived stats data"""
        vrrp_map = {'state': State.healthy}
        vrrp_erros = []
        old_vrrp_map = self._state.get('vrrp', {})

        became_master = int(stats['Became master'])
        released_master = int(stats['Released master'])
        vrrp_map['is_master'] = became_master > released_master
        vrrp_map['is_master_last_update'] = self._current_time
        if vrrp_map['is_master'] != old_vrrp_map.get('is_master'):
            vrrp_map['is_master_last_change'] = self._current_time
            is_master_change_count = old_vrrp_map.get('is_master_change_count', 0) + 1
            LOGGER.info('is_master #%d: %s', is_master_change_count, vrrp_map['is_master'])
            vrrp_map['is_master_change_count'] = is_master_change_count
            if not vrrp_map['is_master']:
                self._cleanup_handler()

        for error_type in ['Packet Errors', 'Authentication Errors']:
            for error_key, error_count in stats.get(error_type, {}).items():
                if int(error_count) > 0:
                    vrrp_map['state'] = State.broken
                    vrrp_erros.append(error_key)

        vrrp_map['state_last_update'] = self._current_time
        if vrrp_map['state'] != old_vrrp_map.get('state'):
            vrrp_map['state_last_change'] = self._current_time
            state_change_count = old_vrrp_map.get('state_change_count', 0) + 1
            LOGGER.info('vrrp_state #%d: %s', state_change_count, vrrp_map['state'])
            vrrp_map['state_change_count'] = state_change_count

        return vrrp_map

    def _periodic_check_local_state(self):
        """Periodically gather local state"""
        with self._lock:
            self._current_time = datetime.now().isoformat()
            self._check_process_info()
            self._check_vrrp_info()
            self._check_connections()
        threading.Timer(self._process_interval, self._periodic_check_local_state).start()

    def start_process_loop(self):
        """Start a loop to periodically gather local state"""
        threading.Thread(target=self._periodic_check_local_state, daemon=True).start()
