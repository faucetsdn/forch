"""Collecting the states of the local system"""

import copy
from datetime import datetime
import logging
import os
import re
import signal
import threading

import psutil
import yaml

import forch.constants as constants

LOGGER = logging.getLogger('localstate')

class LocalStateCollector:
    """Storing local system states"""

    def __init__(self, config, cleanup_handler):
        self._state = {'processes': {}, 'vrrp': {}}
        self._process_state = self._state['processes']
        self._vrrp_state = self._state['vrrp']
        self._target_procs = config.get('processes', {})
        self._check_vrrp = config.get('check_vrrp', False)
        self._current_time = None
        self._process_interval = int(config.get('scan_interval_sec', 60))
        self._lock = threading.Lock()
        self._cleanup_handler = cleanup_handler
        LOGGER.info('Scanning %s processes every %ds',
                    len(self._target_procs), self._process_interval)

    def initialize(self):
        """Initialize LocalStateCollector"""
        if not self._check_vrrp:
            self._vrrp_state['is_master'] = True
        self.start_process_loop()

    def get_process_summary(self):
        """Return a summary of process table"""
        process_state = self.get_process_state()
        return {
            'state': process_state.get('processes_state'),
            'detail': process_state.get('processes_state_detail')
        }

    def get_process_state(self):
        """Get the states of processes"""
        with self._lock:
            return copy.deepcopy(self._process_state)

    def get_vrrp_state(self):
        """Get the local VRRP state"""
        with self._lock:
            return copy.deepcopy(self._vrrp_state)

    def _get_process_info(self):
        """Get the raw information of processes"""

        process_state = self._process_state
        procs = self._get_target_processes()
        broken = []

        # fill up process info
        for target_name, target_map in self._target_procs.items():
            state_map = {}
            process_state[target_name] = state_map
            if target_name not in procs:
                continue
            proc_list = procs[target_name]
            target_count = int(target_map.get('count', 1))
            if len(proc_list) == target_count:
                state_map.update(self._extract_process_state(target_name, proc_list))
                state_map['state'] = constants.STATE_HEALTHY
            else:
                state_map['state'] = 'broken'
                err_detail = f"Process {target_name}: number of process ({len(proc_list)}) " \
                             f"does not match target count ({target_count})"
                state_map['detail'] = err_detail
                LOGGER.error(err_detail)
                broken.append(target_name)

        old_state = process_state.get('processes_state')
        state = constants.STATE_BROKEN if broken else constants.STATE_HEALTHY
        process_state['processes_state'] = state
        process_state['processes_state_last_update'] = self._current_time
        state_detail = 'Processes in broken state: ' + ', '.join(broken) if broken else ''
        process_state['processes_state_detail'] = state_detail
        if state != old_state:
            process_state['processes_state_last_change'] = self._current_time
            state_change_count = process_state.get('processes_state_change_count', 0) + 1
            process_state['processes_state_change_count'] = state_change_count

    def _get_target_processes(self):
        """Get target processes"""
        procs = {}
        for target_name, target_map in self._target_procs.items():
            target_regex = target_map['regex']
            proc_list = procs.setdefault(target_name, [])

            for proc in psutil.process_iter():
                cmd_line_str = ' '.join(proc.cmdline())
                if re.search(target_regex, cmd_line_str):
                    proc_list.append(proc)

        return procs

    def _extract_process_state(self, proc_name, proc_list):
        """Fill process state for a single process"""
        old_proc_map = self._process_state.get(proc_name, {})
        proc_map = copy.deepcopy(old_proc_map)

        cmd_line = ' '.join(proc_list[0].cmdline()) if len(proc_list) == 1 else 'multiple'
        proc_map['cmd_line'] = cmd_line
        create_time = max(proc.create_time() for proc in proc_list)
        proc_map['create_time'] = datetime.fromtimestamp(create_time).isoformat()
        proc_map['create_time_last_update'] = self._current_time

        if proc_map['create_time'] != old_proc_map.get('create_time'):
            proc_map['create_time_last_change'] = self._current_time
            create_time_change_count = old_proc_map.get('create_time_change_count', 0) + 1
            proc_map['create_time_change_count'] = create_time_change_count

        cpu_time_user = 0.0
        cpu_time_system = 0.0
        cpu_time_iowait = None
        memory_rss = 0.0
        memory_vms = 0.0

        for proc in proc_list:
            cpu_time_user += proc.cpu_times().user
            cpu_time_system += proc.cpu_times().system
            if hasattr(proc.cpu_times(), 'iowait'):
                if not cpu_time_iowait:
                    cpu_time_iowait = 0.0
                cpu_time_iowait += proc.cpu_times().iowait

            memory_rss += proc.memory_info().rss / 1e6
            memory_vms += proc.memory_info().vms / 1e6

        proc_map['cpu_times_s'] = {}
        proc_map['cpu_times_s']['user'] = cpu_time_user / len(proc_list)
        proc_map['cpu_times_s']['system'] = cpu_time_system / len(proc_list)
        if cpu_time_iowait:
            proc_map['cpu_times_s']['iowait'] = cpu_time_iowait / len(proc_list)

        proc_map['memory_info_mb'] = {}
        proc_map['memory_info_mb']['rss'] = memory_rss / len(proc_list)
        proc_map['memory_info_mb']['vms'] = memory_vms / len(proc_list)

        return proc_map

    def _get_vrrp_info(self):
        """Get vrrp info"""
        try:
            with open('/var/run/keepalived.pid') as pid_file:
                pid = int(pid_file.readline())
            os.kill(pid, signal.SIGUSR2)
            with open('/tmp/keepalived.stats') as stats_file:
                stats_file.readline()
                stats = yaml.safe_load(stats_file)

                self._vrrp_state = self._extract_vrrp_state(stats)

        except Exception as e:
            LOGGER.error("Cannot get VRRF info: %s", e)

    def _extract_vrrp_state(self, stats):
        """Extract vrrp state from keepalived stats data"""
        vrrp_map = {'state': constants.STATE_HEALTHY}
        vrrp_erros = []
        old_vrrp_map = self._state.get('vrrp', {})

        became_master = int(stats['Became master'])
        released_master = int(stats['Released master'])
        vrrp_map['is_master'] = became_master > released_master
        vrrp_map['is_master_last_update'] = self._current_time
        if vrrp_map['is_master'] != old_vrrp_map.get('is_master'):
            vrrp_map['is_master_last_change'] = self._current_time
            is_master_change_count = old_vrrp_map.get('is_master_change_count', 0) + 1
            vrrp_map['is_master_change_count'] = is_master_change_count
            if not vrrp_map['is_master']:
                self._cleanup_handler()

        for error_type in ['Packet Errors', 'Authentication Errors']:
            for error_key, error_count in stats.get(error_type, {}).items():
                if int(error_count) > 0:
                    vrrp_map['state'] = constants.STATE_BROKEN
                    vrrp_erros.append(error_key)

        vrrp_map['state_last_update'] = self._current_time
        if vrrp_map['state'] != old_vrrp_map.get('state'):
            vrrp_map['state_last_change'] = self._current_time
            is_master_change_count = old_vrrp_map.get('state_change_count', 0) + 1
            vrrp_map['state_change_count'] = is_master_change_count

        return vrrp_map

    def _periodic_get_process_info(self):
        """Periodically gather the processes info"""
        with self._lock:
            self._current_time = datetime.now().isoformat()
            self._get_process_info()
            if self._check_vrrp:
                self._get_vrrp_info()
        threading.Timer(self._process_interval, self._periodic_get_process_info).start()

    def start_process_loop(self):
        """Start a loop to periodically gather the processes info"""
        threading.Thread(target=self._periodic_get_process_info).start()
