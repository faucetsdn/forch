"""Collecting the states of the local system"""

import copy
from datetime import datetime
import os
import re
import signal
import threading
import time

import psutil

from forch.proto.process_state_pb2 import ProcessState, VrrpState
from forch.proto.shared_constants_pb2 import State
from forch.proto.system_state_pb2 import StateSummary
from forch.utils import dict_proto, get_logger

_DEFAULT_KEEPALIVED_PID_FILE = '/var/run/keepalived.pid'

_PROC_ATTRS = ['cmdline', 'cpu_times', 'cpu_percent', 'memory_info']

VRRP_MASTER = 'MASTER'
VRRP_BACKUP = 'BACKUP'
VRRP_FAULT = 'FAULT'
VRRP_ERROR = 'ERROR'


class LocalStateCollector:
    """Storing local system states"""

    def __init__(self, config, cleanup_handler, active_state_handler, metrics):
        self._process_state = {'connections': {}}
        self._vrrp_state = {}
        self._last_error = {}
        self._current_time = None
        self._conn_state = None
        self._conn_state_count = 0
        self._metrics = metrics
        self._lock = threading.Lock()

        self._target_procs = config.processes
        self._check_vrrp = config.check_vrrp
        self._keepalived_pid_file = os.getenv('KEEPALIVED_PID_FILE', _DEFAULT_KEEPALIVED_PID_FILE)
        self._connections = config.connections
        self._process_interval = config.scan_interval_sec or 60

        self._cleanup_handler = cleanup_handler
        self._active_state_handler = active_state_handler

        self._logger = get_logger('lstate')
        self._logger.info(
            'Scanning %s processes every %ds', len(self._target_procs), self._process_interval)

    def initialize(self):
        """Initialize LocalStateCollector"""
        if not self._check_vrrp:
            self._active_state_handler(State.active)

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

    def get_vrrp_summary(self):
        """Return a summary of VRRP states"""
        vrrp_state = self.get_vrrp_state()

        if not self._check_vrrp:
            summary_state = State.healthy
        elif not vrrp_state.vrrp_state:
            summary_state = State.initializing
        elif vrrp_state.vrrp_state == VRRP_MASTER or vrrp_state.vrrp_state == VRRP_BACKUP:
            summary_state = State.healthy
        else:
            summary_state = State.broken

        return dict_proto({
            'state': summary_state,
            'detail': vrrp_state.vrrp_state_detail,
            'change_count': vrrp_state.vrrp_state_change_count,
            'last_change': vrrp_state.vrrp_state_last_change
        }, StateSummary)

    def get_vrrp_state(self):
        """Get VRRP states"""
        with self._lock:
            return dict_proto(self._vrrp_state, VrrpState)

    def _check_process_info(self):
        """Check the raw information of processes"""
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
                self._metrics.update_var('process_state', 1, labels=[target_name])
                state_map.update(state)
                self._last_error.pop(target_name, None)
            else:
                state_map['state'] = State.broken
                self._metrics.update_var('process_state', 0, labels=[target_name])
                if detail != self._last_error.get(target_name):
                    self._logger.error(detail)
                    self._last_error[target_name] = detail
                broken.append(target_name)

            old_process_map = self._process_state.get('processes', {}).get(target_name, {})
            old_state = old_process_map.get('state', State.unknown)
            if state_map['state'] != old_state:
                self._logger.info(
                    'State of process %s changed from %s to %s',
                    target_name, State.State.Name(old_state), State.State.Name(state_map['state']))

        self._process_state['processes'] = process_map
        self._process_state['process_state_last_update'] = self._current_time

        old_state = self._process_state.get('process_state')
        state = State.broken if broken else State.healthy

        old_state_detail = self._process_state.get('process_state_detail')
        state_detail = 'Processes in broken state: ' + ', '.join(broken) if broken else ''

        if state != old_state or state_detail != old_state_detail:
            state_change_count = self._process_state.get('process_state_change_count', 0) + 1
            self._logger.info(
                'process_state #%d is %s: %s', state_change_count, State.State.Name(state),
                state_detail)
            self._process_state['process_state'] = state
            self._process_state['process_state_detail'] = state_detail
            self._process_state['process_state_change_count'] = state_change_count
            self._process_state['process_state_last_change'] = self._current_time

    def _get_target_processes(self):
        """Get target processes"""
        procs = {}
        for proc in psutil.process_iter(attrs=_PROC_ATTRS):
            cmd_line_str = ' '.join(proc.info['cmdline'])
            for target_process_name, target_process_cfg in self._target_procs.items():
                proc_list = procs.setdefault(target_process_name, [])
                if re.search(target_process_cfg.regex, cmd_line_str):
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
            self._logger.info('create_time #%d for %s: %s', change_count, proc_name, create_time)
            proc_map['create_time_change_count'] = change_count
            proc_map['create_time_last_change'] = self._current_time

        try:
            self._aggregate_process_stats(proc_map, proc_list)
        except Exception as e:
            return None, f'Error in extracting info for process {proc_name}: {e}'

        cpu_percent_threshold = self._target_procs[proc_name].cpu_percent_threshold
        if cpu_percent_threshold and proc_map['cpu_percent'] > cpu_percent_threshold:
            self._logger.warning(
                'CPU percent of process %s is %.2f, exceeding threshold %.2f',
                proc_name, proc_map['cpu_percent'], cpu_percent_threshold)

            return proc_map, f'CPU usage is higher than threshold {cpu_percent_threshold}'

        return proc_map, None

    def _aggregate_process_stats(self, proc_map, proc_list):
        cpu_time_user = 0.0
        cpu_time_system = 0.0
        cpu_time_iowait = None
        cpu_percent = 0.0
        memory_rss = 0.0
        memory_vms = 0.0

        for proc in proc_list:
            cpu_time_user += proc.info['cpu_times'].user
            cpu_time_system += proc.info['cpu_times'].system
            if hasattr(proc.info['cpu_times'], 'iowait'):
                if not cpu_time_iowait:
                    cpu_time_iowait = 0.0
                cpu_time_iowait += proc.cpu_times().iowait

            cpu_percent += proc.info['cpu_percent']

            memory_rss += proc.info['memory_info'].rss / 1e6
            memory_vms += proc.info['memory_info'].vms / 1e6

        proc_map['cpu_times_s'] = {}
        proc_map['cpu_times_s']['user'] = cpu_time_user / len(proc_list)
        proc_map['cpu_times_s']['system'] = cpu_time_system / len(proc_list)
        if cpu_time_iowait:
            proc_map['cpu_times_s']['iowait'] = cpu_time_iowait / len(proc_list)

        proc_map['cpu_percent'] = cpu_percent / len(proc_list)

        proc_map['memory_info_mb'] = {}
        proc_map['memory_info_mb']['rss'] = memory_rss / len(proc_list)
        proc_map['memory_info_mb']['vms'] = memory_vms / len(proc_list)

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
            self._logger.info('conn_state #%d: %s', self._conn_state_count, conn_state)
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
                        self._logger.error('Processing netstat entry: %s', e)

        return connections

    def _extract_conn(self, connections, port):
        foreign_addresses = {}
        process_entry = None
        for foreign_address in connections:
            entry = connections[foreign_address]
            if entry['local_port'] == port:
                new_process_entry = entry['process_info']
                if process_entry and new_process_entry != process_entry:
                    self._logger.error(
                        'Inconsistent process entry for %s: %s != %s', port, process_entry,
                        new_process_entry)
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
        vrrp_state = None
        error_detail = None
        try:
            if not self._check_vrrp:
                return

            with open(self._keepalived_pid_file) as pid_file:
                pid = int(pid_file.readline())
            os.kill(pid, signal.SIGUSR1)
            time.sleep(1)
            with open('/tmp/keepalived.data') as stats_file:
                for line in stats_file:
                    match = re.search('State = (MASTER|BACKUP|FAULT)', line)
                    if not match:
                        continue
                    vrrp_state = match.group(1)
                    break

            if not vrrp_state:
                vrrp_state = VRRP_ERROR
                error_detail = 'Could not find matching states'

        except Exception as e:
            vrrp_state = VRRP_ERROR
            error_detail = f'Cannot get VRRP info: {e}'

        finally:
            self._vrrp_state.update(self._handle_vrrp_state(vrrp_state, error_detail))

    def _handle_vrrp_state(self, vrrp_state, error_detail=None):
        """Extract vrrp state from keepalived stats data"""
        vrrp_map = {'vrrp_state': vrrp_state}
        old_vrrp_map = copy.deepcopy(self._vrrp_state)
        old_vrrp_state = old_vrrp_map.get('vrrp_state')
        old_vrrp_state_detail = old_vrrp_map.get('vrrp_state_detail')

        if vrrp_state != old_vrrp_state or error_detail != old_vrrp_state_detail:
            vrrp_map['vrrp_state_last_change'] = self._current_time
            state_change_count = old_vrrp_map.get('vrrp_state_change_count', 0) + 1
            vrrp_map['vrrp_state_change_count'] = state_change_count

            self._logger.info(
                'VRRP state #%d: %s, %s', vrrp_map['vrrp_state_change_count'], vrrp_state,
                error_detail)

            if vrrp_state == VRRP_MASTER:
                vrrp_map['vrrp_state_detail'] = None
                self._active_state_handler(State.active)
            elif vrrp_state == VRRP_BACKUP:
                vrrp_map['vrrp_state_detail'] = None
                self._active_state_handler(State.inactive)
            elif vrrp_state == VRRP_FAULT:
                vrrp_map['vrrp_state_detail'] = 'VRRP is in fault state'
                self._active_state_handler(State.broken)
            elif vrrp_state == VRRP_ERROR:
                vrrp_map['vrrp_state_detail'] = error_detail
                self._active_state_handler(State.broken)
            else:
                self._logger.error('Unknown VRRP state: %s', vrrp_state)

            if vrrp_state != VRRP_MASTER:
                self._cleanup_handler()

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
