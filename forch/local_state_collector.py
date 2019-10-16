"""Collecting the states of the local system"""

from datetime import datetime
import logging
import re

import psutil

import forch.constants as constants

LOGGER = logging.getLogger('localstate')

class LocalStateCollector:
    """Storing local system states"""

    def __init__(self):
        self._state = {'processes': {}}
        self._process_state = self._state['processes']
        self._target_procs = {'faucet':     ('ryu-manager', r'faucet\.faucet'),
                              'gauge':      ('ryu-manager', r'faucet\.gauge'),
                              'keepalived': ('keepalived', r'keepalived'),
                              'forch':      ('python', r'forchestrator\.py'),
                              'bosun':      ('dunsel_watcher', r'bosun')}

    def get_process_summary(self):
        """Return a summary of process table"""
        process_state = self.get_process_state()
        return {
            'state': process_state.get('processes_state'),
            'detail': process_state.get('processes_state_detail')
        }

    def get_process_state(self):
        """Get the information of processes in proc_set"""

        self._process_state.clear()
        procs = self._get_target_processes()
        broken = []

        # fill up process info
        for target_name in self._target_procs:
            state_map = {}
            self._process_state[target_name] = state_map
            if target_name in procs:
                proc = procs[target_name]
                if proc:
                    state_map.update(self._extract_process_state(proc))
                    state_map['state'] = constants.STATE_HEALTHY
                else:
                    state_map['state'] = 'broken'
                    state_map['detail'] = 'Multiple processes found'
                    broken.append(target_name)
            else:
                state_map['state'] = 'broken'
                state_map['detail'] = 'Process not found'
                broken.append(target_name)

        state = constants.STATE_BROKEN if broken else constants.STATE_HEALTHY
        self._process_state['processes_state'] = state
        self._process_state['processes_state_detail'] = ', '.join(broken)

        return self._process_state

    def _get_target_processes(self):
        """Get target processes"""
        procs = {}
        for proc in psutil.process_iter():
            for target_name, (target_cmd, target_regex) in self._target_procs.items():
                if proc.name() != target_cmd:
                    continue
                cmd_line_str = ''.join(proc.cmdline())
                if re.search(target_regex, cmd_line_str):
                    if target_name in procs:
                        LOGGER.error("Duplicate process: %s", str(procs[target_name]))
                        procs[target_name] = None
                        break
                    procs[target_name] = proc
        return procs

    def _extract_process_state(self, proc):
        """Fill process state"""
        proc_map = {}

        proc_map['cmd_line'] = ' '.join(proc.cmdline())
        proc_map['create_time'] = datetime.fromtimestamp(proc.create_time()).isoformat()
        proc_map['cpu_times_s'] = {}
        proc_map['cpu_times_s']['user'] = proc.cpu_times().user
        proc_map['cpu_times_s']['system'] = proc.cpu_times().system
        if hasattr(proc.cpu_times(), 'iowait'):
            proc_map['cpu_times_s']['iowait'] = proc.cpu_times().iowait

        proc_map['memory_info_mb'] = {}
        proc_map['memory_info_mb']['rss'] = proc.memory_info().rss / 1e6
        proc_map['memory_info_mb']['vms'] = proc.memory_info().vms / 1e6
        return proc_map
