"""Orchestrator component for controlling a Faucet SDN"""

from datetime import datetime
import logging
import os
import threading
import time

from google.protobuf.message import Message
from forch.proto import faucet_event_pb2 as FaucetEvent

from faucet import config_parser

import forch.faucet_event_client
import forch.faucetizer as faucetizer

from forch.authenticator import Authenticator
from forch.cpn_state_collector import CPNStateCollector
from forch.config_file_watcher import ConfigFileWatcher
from forch.faucet_state_collector import FaucetStateCollector
from forch.forch_metrics import ForchMetrics
from forch.heartbeat_scheduler import HeartbeatScheduler
from forch.local_state_collector import LocalStateCollector
from forch.varz_state_collector import VarzStateCollector

from forch.utils import yaml_proto

from forch.__version__ import __version__

from forch.proto.devices_state_pb2 import DevicesState, DeviceBehavior
from forch.proto.shared_constants_pb2 import State
from forch.proto.system_state_pb2 import SystemState

LOGGER = logging.getLogger('forch')

_STRUCTURAL_CONFIG_DEFAULT = 'faucet.yaml'
_BEHAVIORAL_CONFIG_DEFAULT = 'faucet.yaml'
_SEGMENTS_VLAN_DEFAULT = 'segments-to-vlans.yaml'
_DEFAULT_PORT = 9019
_PROMETHEUS_HOST = '127.0.0.1'


class Forchestrator:
    """Main class encompassing faucet orchestrator components for dynamically
    controlling faucet ACLs at runtime"""

    _DETAIL_FORMAT = '%s is %s: %s'

    def __init__(self, config):
        self._config = config
        self._structural_config_file = None
        self._behavioral_config_file = None
        self._faucet_events = None
        self._start_time = datetime.fromtimestamp(time.time()).isoformat()

        self._faucet_collector = None
        self._varz_collector = None
        self._local_collector = None
        self._cpn_collector = None

        self._faucetizer = None
        self._authenticator = None
        self._faucetize_scheduler = None
        self._config_file_watcher = None
        self._faucet_state_scheduler = None

        self._initialized = False
        self._active_state = State.initializing
        self._active_state_lock = threading.Lock()

        self._config_summary = None
        self._metrics = None

    def initialize(self):
        """Initialize forchestrator instance"""
        self._metrics = ForchMetrics(self._config.varz_interface)
        self._metrics.start()
        self._faucet_collector = FaucetStateCollector(self._config.event_client)
        self._faucet_collector.set_placement_callback(self._process_device_placement)
        self._faucet_state_scheduler = HeartbeatScheduler(interval_sec=1)
        self._faucet_state_scheduler.add_callback(self._faucet_collector.heartbeat_update)

        self._local_collector = LocalStateCollector(
            self._config.process, self.cleanup, self.handle_active_state, metrics=self._metrics)
        self._cpn_collector = CPNStateCollector()

        prom_port = os.getenv('PROMETHEUS_PORT')
        if not prom_port:
            raise Exception("PROMETHEUS_PORT is not set")
        prom_url = f"http://{_PROMETHEUS_HOST}:{prom_port}"
        self._varz_collector = VarzStateCollector(prom_url)

        LOGGER.info('Attaching event channel...')
        self._faucet_events = forch.faucet_event_client.FaucetEventClient(
            self._config.event_client)
        self._local_collector.initialize()
        self._cpn_collector.initialize()
        LOGGER.info('Using peer controller %s', self._get_peer_controller_url())

        if self._calculate_config_files():
            self._initialize_faucetizer()
            self._faucetizer.reload_structural_config()
        self._attempt_authenticator_initialise()
        self._process_static_device_placement()
        self._process_static_device_behavior()
        if self._faucetizer:
            self._faucetizer.flush_behavioral_config(force=True)

        self._validate_config_files()

        while True:
            time.sleep(10)
            try:
                self._get_varz_config()
                break
            except Exception as e:
                LOGGER.error('Waiting for varz config: %s', e)

        self._register_handlers()
        self.start()
        self._initialized = True

    def _attempt_authenticator_initialise(self):
        orch_config = self._config.orchestration
        if not orch_config.HasField('auth_config'):
            return
        LOGGER.info('Initializing authenticator')
        self._authenticator = Authenticator(orch_config.auth_config,
                                            self.handle_auth_result,
                                            metrics=self._metrics)

    def _process_static_device_placement(self):
        static_placement_file = self._config.orchestration.static_device_placement
        if not static_placement_file:
            return
        placement_file = os.path.join(
            os.getenv('FAUCET_CONFIG_DIR'), static_placement_file)
        devices_state = yaml_proto(placement_file, DevicesState)
        for eth_src, device_placement in devices_state.device_mac_placements.items():
            self._process_device_placement(eth_src, device_placement, static=True)

    def _process_static_device_behavior(self):
        static_behaviors_file = self._config.orchestration.static_device_behavior
        if not static_behaviors_file:
            return
        static_behaviors_path = os.path.join(
            os.getenv('FAUCET_CONFIG_DIR'), static_behaviors_file)
        devices_state = faucetizer.load_devices_state(static_behaviors_path)
        for mac, device_behavior in devices_state.device_mac_behaviors.items():
            self._process_device_behavior(mac, device_behavior, static=True)

    def _calculate_config_files(self):
        orch_config = self._config.orchestration

        behavioral_config_file = (orch_config.behavioral_config_file or
                                  os.getenv('FAUCET_CONFIG') or
                                  _BEHAVIORAL_CONFIG_DEFAULT)
        self._behavioral_config_file = os.path.join(
            os.getenv('FAUCET_CONFIG_DIR'), behavioral_config_file)

        structural_config_file = orch_config.structural_config_file
        if structural_config_file:
            self._structural_config_file = os.path.join(
                os.getenv('FAUCET_CONFIG_DIR'), structural_config_file)

            if not os.path.exists(self._structural_config_file):
                raise Exception(
                    f'Structural config file does not exist: {self._structural_config_file}')

            return True

        return False

    def _validate_config_files(self):
        if not os.path.exists(self._behavioral_config_file):
            raise Exception(
                f'Behavioral config file does not exist: {self._behavioral_config_file}')

        if self._structural_config_file == self._behavioral_config_file:
            raise Exception(
                'Structural and behavioral config file cannot be the same: '
                f'{self._behavioral_config_file}')

    def _initialize_faucetizer(self):
        orch_config = self._config.orchestration

        segments_vlans_file = orch_config.segments_vlans_file or _SEGMENTS_VLAN_DEFAULT
        segments_vlans_path = os.path.join(os.getenv('FAUCET_CONFIG_DIR'), segments_vlans_file)
        LOGGER.info('Loading segment to vlan mappings from %s', segments_vlans_path)
        segments_to_vlans = faucetizer.load_segments_to_vlans(segments_vlans_path)

        self._faucetizer = faucetizer.Faucetizer(
            orch_config, self._structural_config_file, segments_to_vlans.segments_to_vlans,
            self._behavioral_config_file, self._reregister_acl_file_handlers)

        if orch_config.faucetize_interval_sec:
            self._faucetize_scheduler = HeartbeatScheduler(orch_config.faucetize_interval_sec)

            update_write_faucet_config = (lambda: (
                self._faucetizer.reload_structural_config(),
                self._faucetizer.flush_behavioral_config(force=True)))
            self._faucetize_scheduler.add_callback(update_write_faucet_config)
        else:
            self._config_file_watcher = ConfigFileWatcher(
                self._structural_config_file, self._faucetizer.reload_structural_config)

    def _reregister_acl_file_handlers(self, old_acl_files, new_acl_files,):
        self._config_file_watcher.unregister_file_handlers(old_acl_files)
        for new_acl_file in new_acl_files:
            self._config_file_watcher.register_file_handler(
                new_acl_file, self._faucetizer.reload_acl_file)

    def initialized(self):
        """If forch is initialized or not"""
        return self._initialized

    def _process_device_placement(self, eth_src, device_placement, static=False):
        """Call device placement API for faucetizer/authenticator"""
        if self._faucetizer:
            self._faucetizer.process_device_placement(eth_src, device_placement, static=static)
        if self._authenticator:
            self._authenticator.process_device_placement(eth_src, device_placement)

    def _process_device_behavior(self, mac, device_behavior, static=False):
        """Function interface of processing device behavior"""
        if self._faucetizer:
            self._faucetizer.process_device_behavior(mac, device_behavior, static=static)

    def handle_auth_result(self, mac, segment, role):
        """Method passed as callback to authenticator to forward auth results"""
        device_behavior = DeviceBehavior(segment=segment, role=role)
        self._process_device_behavior(mac, device_behavior)

    def _register_handlers(self):
        fcoll = self._faucet_collector
        self._faucet_events.register_handlers([
            (FaucetEvent.ConfigChange, self._process_config_change),
            (FaucetEvent.DpChange, lambda event: fcoll.process_dp_change(
                event.timestamp, event.dp_name, None, event.reason == "cold_start")),
            (FaucetEvent.LagChange, lambda event: fcoll.process_lag_state(
                event.timestamp, event.dp_name, event.port_no, event.state)),
            (FaucetEvent.StackState, lambda event: fcoll.process_stack_state(
                event.timestamp, event.dp_name, event.port, event.state)),
            (FaucetEvent.StackTopoChange, fcoll.process_stack_topo_change_event),
            (FaucetEvent.PortChange, fcoll.process_port_change),
            (FaucetEvent.L2Learn, lambda event: fcoll.process_port_learn(
                event.timestamp, event.dp_name, event.port_no, event.eth_src, event.l3_src_ip)),
            (FaucetEvent.L2Expire, lambda event: fcoll.process_port_expire(
                event.timestamp, event.dp_name, event.port_no, event.eth_src)),
        ])

    def _get_varz_config(self):
        metrics = self._varz_collector.get_metrics()
        varz_hash_info = metrics['faucet_config_hash_info']
        assert len(varz_hash_info.samples) == 1, 'exactly one config hash info not found'
        varz_config_hashes = varz_hash_info.samples[0].labels['hashes']
        varz_config_error = varz_hash_info.samples[0].labels['error']

        if varz_config_error:
            raise Exception(f'Varz config error: {varz_config_error}')

        return metrics, varz_config_hashes

    def _restore_states(self):
        # Make sure the event socket is connected so there's no loss of information. Ordering
        # is important here, need to connect the socket before scraping current state to avoid
        # loss of events inbetween.
        assert self._faucet_events.event_socket_connected, 'restore states without connection'

        # Restore config first before restoring all state from varz.
        metrics, varz_config_hashes = self._get_varz_config()
        self._restore_faucet_config(time.time(), varz_config_hashes)

        event_horizon = self._faucet_collector.restore_states_from_metrics(metrics)
        self._faucet_events.set_event_horizon(event_horizon)

    def _restore_faucet_config(self, timestamp, config_hash):
        config_info, faucet_dps, _ = self._get_faucet_config()
        assert config_hash == config_info['hashes'], 'config hash info does not match'
        self._faucet_collector.process_dataplane_config_change(timestamp, faucet_dps)

    def _process_config_change(self, event):
        self._faucet_collector.process_dp_config_change(
            event.timestamp, event.dp_name, event.restart_type, event.dp_id)
        if event.config_hash_info.hashes:
            self._restore_faucet_config(event.timestamp, event.config_hash_info.hashes)

    def _faucet_events_connect(self):
        LOGGER.info('Attempting faucet event sock connection...')
        time.sleep(1)
        try:
            self._faucet_events.connect()
            self._restore_states()
            self._faucet_collector.set_state_restored(True)
        except Exception as e:
            LOGGER.error("Cannot restore states or connect to faucet", exc_info=True)
            self._faucet_collector.set_state_restored(False, e)

    def main_loop(self):
        """Main event processing loop"""
        LOGGER.info('Entering main event loop...')
        try:
            while self._faucet_events:
                while not self._faucet_events.event_socket_connected:
                    self._faucet_events_connect()
                self._process_faucet_event()
        except KeyboardInterrupt:
            LOGGER.info('Keyboard interrupt. Exiting.')
            self._faucet_events.disconnect()
        except Exception as e:
            LOGGER.error("Exception: %s", e)
            raise

    def start(self):
        """Start forchestrator components"""
        if self._faucetize_scheduler:
            self._faucetize_scheduler.start()
        if self._config_file_watcher:
            self._config_file_watcher.start()
        if self._faucet_state_scheduler:
            self._faucet_state_scheduler.start()
        if self._metrics:
            self._metrics.update_var('forch_version', {'version': __version__})

    def stop(self):
        """Stop forchestrator components"""
        if self._faucetize_scheduler:
            self._faucetize_scheduler.stop()
        if self._faucet_state_scheduler:
            self._faucet_state_scheduler.stop()
        if self._authenticator:
            self._authenticator.stop()
        if self._config_file_watcher:
            self._config_file_watcher.stop()
        if self._metrics:
            self._metrics.stop()

    def _process_faucet_event(self):
        try:
            event = self._faucet_events.next_event(blocking=True)
        except Exception as e:
            LOGGER.warning('While processing event %s exception: %s', event, str(e))
            raise e

    def _get_controller_info(self, target):
        controllers = self._config.site.controllers
        if target not in controllers:
            return (f'missing_target_{target}', _DEFAULT_PORT)
        controller = controllers[target]
        host = controller.fqdn or target
        port = controller.port or _DEFAULT_PORT
        return (host, port)

    def get_local_port(self):
        """Get the local port for this instance"""
        info = self._get_controller_info(self._get_controller_name())
        LOGGER.info('Local controller is at %s on %s', info[0], info[1])
        return int(info[1])

    def _make_controller_url(self, info):
        return f'http://{info[0]}:{info[1]}'

    def _get_local_controller_url(self):
        return self._make_controller_url(self._get_controller_info(self._get_controller_name()))

    def _get_peer_controller_name(self):
        name = self._get_controller_name()
        controllers = self._config.site.controllers
        if name not in controllers:
            return f'missing_controller_name_{name}'
        if len(controllers) != 2:
            return 'num_controllers_%s' % len(controllers)
        things = set(controllers.keys())
        things.remove(name)
        return list(things)[0]

    def _get_peer_controller_info(self):
        return self._get_controller_info(self._get_peer_controller_name())

    def _get_peer_controller_url(self):
        return self._make_controller_url(self._get_peer_controller_info())

    def _get_controller_name(self):
        return os.getenv('CONTROLLER_NAME')

    def get_system_state(self, path, params):
        """Get an overview of the system state"""
        system_state = SystemState()
        self._populate_versions(system_state.versions)
        system_state.peer_controller_url = self._get_peer_controller_url()
        system_state.summary_sources.CopyFrom(self._get_system_summary(path))
        system_state.site_name = self._config.site.name or 'unknown'
        system_state.controller_name = self._get_controller_name()
        system_state.config_summary.CopyFrom(self._config_summary)
        self._distill_summary(system_state.summary_sources, system_state)
        return system_state

    def _distill_summary(self, summaries, system_state):
        try:
            start_time = self._start_time
            summary_fields = summaries.ListFields()
            summary_values = [value[1] for value in summary_fields]
            change_counts = list(map(lambda subsystem:
                                     subsystem.change_count or 0, summary_values))
            last_changes = list(map(lambda subsystem:
                                    subsystem.last_change or start_time, summary_values))
            last_updates = list(map(lambda subsystem:
                                    subsystem.last_update or start_time, summary_values))
            summary, detail = self._get_combined_summary(summaries)
            system_state.system_state = summary
            system_state.system_state_detail = detail
            LOGGER.info('system_state_change_count sources: %s', change_counts)
            system_state.system_state_change_count = sum(change_counts)
            system_state.system_state_last_change = max(last_changes)
            system_state.system_state_last_update = max(last_updates)
        except Exception as e:
            system_state.system_state = State.broken
            system_state.system_state_detail = str(e)
            LOGGER.exception(e)

    def _get_combined_summary(self, summary):
        controller_state, controller_state_detail = self._get_controller_state()
        if controller_state != State.active:
            return controller_state, controller_state_detail

        has_error = False
        has_warning = False
        details = []
        for field, subsystem in summary.ListFields():
            state = subsystem.state
            if state in (State.down, State.broken):
                has_error = True
                details.append(field.name)
            elif state != State.healthy:
                has_warning = True
                details.append(field.name)
        if details:
            detail = 'broken subsystems: ' + ', '.join(details)
        else:
            detail = 'n/a'

        if not self._faucet_events.event_socket_connected:
            has_error = True
            detail += '. Faucet disconnected.'

        if has_error:
            return State.broken, detail
        if has_warning:
            return State.damaged, detail
        return State.healthy, detail

    def _get_system_summary(self, path):
        states = SystemState.SummarySources()
        states.cpn_state.CopyFrom(self._cpn_collector.get_cpn_summary())
        states.process_state.CopyFrom(self._local_collector.get_process_summary())
        states.dataplane_state.CopyFrom(self._faucet_collector.get_dataplane_summary())
        states.switch_state.CopyFrom(self._faucet_collector.get_switch_summary())
        states.list_hosts.CopyFrom(self._faucet_collector.get_host_summary())
        url_base = self._extract_url_base(path)
        for field, value in states.ListFields():
            value.detail_url = f'{url_base}/?{field.name}'
        return states

    def _extract_url_base(self, path):
        slash = path.find('/')
        host = path[:slash]
        return f'http://{host}'

    def _augment_state_reply(self, reply, path):
        url = self._extract_url_base(path)
        if isinstance(reply, Message):
            reply.system_state_url = url
        else:
            reply['system_state_url'] = url
        return reply

    def _get_controller_state(self):
        with self._active_state_lock:
            active_state = self._active_state
            if active_state == State.initializing:
                return State.initializing, 'Initializing'
            if active_state == State.inactive:
                detail = 'This controller is inactive. Please view peer controller.'
                return State.inactive, detail
            if active_state != State.active:
                return State.broken, 'Internal error'

        cpn_state = self._cpn_collector.get_cpn_state()
        peer_controller = self._get_peer_controller_name()

        if peer_controller in cpn_state.cpn_nodes:
            peer_controller_state = cpn_state.cpn_nodes[peer_controller].state
        else:
            LOGGER.error('Cannot get peer controller state for %s', peer_controller)
            peer_controller_state = State.broken

        if cpn_state.cpn_state == State.initializing:
            return State.initializing, 'Initializing'

        if peer_controller_state != State.healthy:
            return State.split, 'Lost reachability to peer controller.'

        return State.active, None

    def _get_faucet_config_hash_info(self, new_conf_hashes):
        # Code taken from faucet/valves_manager.py parse_configs.
        new_present_conf_hashes = [
            (conf_file, conf_hash) for conf_file, conf_hash in sorted(new_conf_hashes.items())
            if conf_hash is not None]
        conf_files = [conf_file for conf_file, _ in new_present_conf_hashes]
        conf_hashes = [conf_hash for _, conf_hash in new_present_conf_hashes]
        return dict(config_files=','.join(conf_files), hashes=','.join(conf_hashes))

    def _get_faucet_config(self):
        try:
            (new_conf_hashes, _, new_dps, top_conf) = config_parser.dp_parser(
                self._behavioral_config_file, 'fconfig')
            config_hash_info = self._get_faucet_config_hash_info(new_conf_hashes)
            self._config_summary = SystemState.ConfigSummary()
            for file_name, file_hash in new_conf_hashes.items():
                LOGGER.info('Loaded conf %s as %s', file_name, file_hash)
                self._config_summary.hashes[file_name] = file_hash
            for warning, message in self._config_warnings(top_conf):
                LOGGER.warning('Config warning %s: %s', warning, message)
                self._config_summary.warnings[warning] = message
            return config_hash_info, new_dps, top_conf
        except Exception as e:
            LOGGER.error('Cannot read faucet config: %s', e)
            raise e

    def _config_warnings(self, config):
        warnings = []
        for dp_name, dp_obj in config['dps'].items():
            if 'faucet_dp_mac' in dp_obj:
                warnings.append((dp_name, 'faucet_dp_mac defined'))
            if 'interface_ranges' in dp_obj:
                warnings.append((dp_name, 'interface_ranges defined'))
            for if_name, if_obj in dp_obj['interfaces'].items():
                if_key = '%s:%02d' % (dp_name, int(if_name))
                is_egress = 1 if 'lacp' in if_obj else 0
                is_stack = 1 if 'stack' in if_obj else 0
                is_access = 1 if 'native_vlan' in if_obj else 0
                if (is_egress + is_stack + is_access) != 1:
                    warnings.append((if_key, 'misconfigured interface config: %d %d %d' %
                                     (is_egress, is_stack, is_access)))
                if 'loop_protect_external' in if_obj:
                    warnings.append((if_key, 'deprecated loop_protect_external'))
                if is_access and 'max_hosts' not in if_obj:
                    warnings.append((if_key, 'missing recommended max_hosts'))
        return warnings

    def _populate_versions(self, versions):
        versions.forch = __version__
        try:
            versions.faucet = os.popen('faucet --version').read().strip().split()[1]
        except Exception as e:
            versions.faucet = f'Cannot get faucet version: {e}'

    def cleanup(self):
        """Clean up relevant internal data in all collectors"""
        self._faucet_collector.cleanup()

    def handle_active_state(self, active_state):
        """Handler for local state collector to handle controller active state"""
        with self._active_state_lock:
            self._active_state = active_state
        self._faucet_collector.set_active(active_state)

    def get_switch_state(self, path, params):
        """Get the state of the switches"""
        switch = params.get('switch')
        port = params.get('port')
        host = self._extract_url_base(path)
        reply = self._faucet_collector.get_switch_state(switch, port, host)
        return self._augment_state_reply(reply, path)

    def get_dataplane_state(self, path, params):
        """Get the dataplane state overview"""
        reply = self._faucet_collector.get_dataplane_state()
        return self._augment_state_reply(reply, path)

    def get_host_path(self, path, params):
        """Get active host path"""
        eth_src = params.get('eth_src')
        eth_dst = params.get('eth_dst')
        to_egress = params.get('to_egress') == 'true'
        reply = self._faucet_collector.get_host_path(eth_src, eth_dst, to_egress)
        return self._augment_state_reply(reply, path)

    def get_list_hosts(self, path, params):
        """List learned access devices"""
        eth_src = params.get('eth_src')
        host = self._extract_url_base(path)
        reply = self._faucet_collector.get_list_hosts(host, eth_src)
        return self._augment_state_reply(reply, path)

    def get_cpn_state(self, path, params):
        """Get CPN state"""
        reply = self._cpn_collector.get_cpn_state()
        return self._augment_state_reply(reply, path)

    def get_process_state(self, path, params):
        """Get certain processes state on the controller machine"""
        reply = self._local_collector.get_process_state()
        return self._augment_state_reply(reply, path)

    def get_sys_config(self, path, params):
        """Get overall config from faucet config file"""
        try:
            _, _, faucet_config = self._get_faucet_config()
            reply = {
                'faucet': faucet_config
            }
            return self._augment_state_reply(reply, path)
        except Exception as e:
            return f"Cannot read faucet config: {e}"
