"""Orchestrator component for controlling a Faucet SDN"""

import abc
from datetime import datetime
import functools
import os
import threading
import time

from google.protobuf.message import Message

from faucet import config_parser

import forch.faucet_event_client
import forch.faucetizer as faucetizer

from forch.authenticator import Authenticator
from forch.cpn_state_collector import CPNStateCollector
from forch.device_report_server import DeviceReportServer
from forch.file_change_watcher import FileChangeWatcher
from forch.faucet_state_collector import FaucetStateCollector
from forch.forch_metrics import ForchMetrics, VarzUpdater
from forch.forch_proxy import ForchProxy
from forch.heartbeat_scheduler import HeartbeatScheduler
from forch.local_state_collector import LocalStateCollector
from forch.port_state_manager import PortStateManager
from forch.varz_state_collector import VarzStateCollector
from forch.utils import (
    get_logger, proto_dict, yaml_proto, FaucetEventOrderError, MetricsFetchingError)

from forch.__version__ import __version__

from forch.proto.devices_state_pb2 import DevicesState, DeviceBehavior, DevicePlacement
import forch.proto.faucet_event_pb2 as FaucetEvent
from forch.proto.shared_constants_pb2 import State
from forch.proto.system_state_pb2 import SystemState

_STRUCTURAL_CONFIG_DEFAULT = 'faucet.yaml'
_BEHAVIORAL_CONFIG_DEFAULT = 'faucet.yaml'
_FORCH_CONFIG_DIR_DEFAULT = '/etc/forch'
_FAUCET_CONFIG_DIR_DEFAULT = '/etc/faucet'
_DEFAULT_PORT = 9019
_FAUCET_PROM_HOST = '127.0.0.1'
_FAUCET_PROM_PORT_DEFAULT = 9302
_GAUGE_PROM_HOST = '127.0.0.1'
_GAUGE_PROM_PORT_DEFAULT = 9303
_CONFIG_HASH_VERIFICATION_TIMEOUT_SEC_DEFAULT = 30

_TARGET_FAUCET_METRICS = (
    'port_status',
    'port_lacp_state',
    'port_lacp_role',
    'dp_status',
    'learned_l2_port',
    'port_stack_state',
    'faucet_config_hash_info',
    'faucet_event_id',
    'dp_root_hop_port',
    'faucet_stack_root_dpid',
    'faucet_config_reload_cold',
    'faucet_config_reload_warm',
    'ryu_config'
)

_TARGET_GAUGE_METRICS = (
    'flow_packet_count_vlan_acl',
    'flow_packet_count_port_acl',
    'flow_packet_count_vlan'
)

ACTIVE_STATE = 'active_state'
STATIC_BEHAVIORAL_FILE = 'static_behavior_file'
SEGMENTS_VLANS_FILE = 'segments_vlans_file'
TAIL_ACL_CONFIG = 'tail_acl_config'


class OrchestrationManager(abc.ABC):
    """Interface collecting the methods that manage orchestration"""

    @abc.abstractmethod
    def reregister_include_file_watchers(self, old_include_files, new_include_files):
        """reregister the include file watchers"""

    @abc.abstractmethod
    def reset_faucet_config_writing_time(self):
        """reset config writing time"""


class Forchestrator(VarzUpdater, OrchestrationManager):
    """Main class encompassing faucet orchestrator components for dynamically
    controlling faucet ACLs at runtime"""

    _DETAIL_FORMAT = '%s is %s: %s'

    def __init__(self, config):
        self._config = config
        self._structural_config_file = None
        self._behavioral_config_file = None
        self._forch_config_dir = None
        self._faucet_config_dir = None
        self._gauge_config_file = None
        self._segments_vlans_file = None
        self._faucet_events = None
        self._start_time = datetime.fromtimestamp(time.time()).isoformat()
        self._faucet_prom_endpoint = None
        self._gauge_prom_endpoint = None
        self._behavioral_config = None

        self._faucet_collector = None
        self._local_collector = None
        self._cpn_collector = None
        self._varz_collector = None

        self._faucetizer = None
        self._authenticator = None
        self._faucetize_scheduler = None
        self._config_file_watcher = None
        self._faucet_state_scheduler = None
        self._gauge_metrics_scheduler = None
        self._device_report_server = None
        self._port_state_manager = None

        self._initialized = False
        self._active_state = State.initializing
        self._active_state_lock = threading.Lock()

        self._should_enable_faucetizer = False
        self._should_ignore_auth_result = False

        self._config_errors = {}
        self._system_errors = {}
        self._faucet_config_summary = SystemState.ConfigSummary()
        self._metrics = None
        self._varz_proxy = None

        self._last_faucet_config_writing_time = None
        self._last_received_faucet_config_hash = None
        self._config_hash_verification_timeout_sec = (
            self._config.event_client.config_hash_verification_timeout_sec or
            _CONFIG_HASH_VERIFICATION_TIMEOUT_SEC_DEFAULT)

        self._states_lock = threading.Lock()
        self._timer_lock = threading.Lock()
        self._logger = get_logger('forch')

    def initialize(self):
        """Initialize forchestrator instance"""
        self._should_enable_faucetizer = self._calculate_orchestration_config()

        self._metrics = ForchMetrics(self._config.varz_interface)
        self._metrics.start()

        self._varz_collector = VarzStateCollector()
        self._faucet_collector = FaucetStateCollector(
            self._config, is_faucetizer_enabled=self._should_enable_faucetizer)
        self._faucet_collector.set_placement_callback(self._process_device_placement)
        self._faucet_collector.set_get_gauge_metrics(
            lambda: self._varz_collector.retry_get_metrics(
                self._gauge_prom_endpoint, _TARGET_GAUGE_METRICS))
        self._faucet_collector.set_get_dva_state(
            (lambda switch, port:
             self._faucetizer.get_dva_state(switch, port) if self._faucetizer else None))
        self._faucet_collector.set_forch_metrics(self._metrics)
        self._faucet_state_scheduler = HeartbeatScheduler(interval_sec=1)
        self._faucet_state_scheduler.add_callback(
            self._faucet_collector.heartbeat_update_stack_state)
        self._faucet_state_scheduler.add_callback(self._verify_config_hash)

        gauge_metrics_interval_sec = self._config.dataplane_monitoring.gauge_metrics_interval_sec
        if gauge_metrics_interval_sec:
            self._initialize_gauge_metrics_scheduler(gauge_metrics_interval_sec)

        self._local_collector = LocalStateCollector(
            self._config.process, self.cleanup, self.handle_active_state, metrics=self._metrics)
        self._cpn_collector = CPNStateCollector(self._config.cpn_monitoring)

        faucet_prom_port = os.getenv('FAUCET_PROM_PORT', str(_FAUCET_PROM_PORT_DEFAULT))
        self._faucet_prom_endpoint = f"http://{_FAUCET_PROM_HOST}:{faucet_prom_port}"

        gauge_prom_port = os.getenv('GAUGE_PROM_PORT', str(_GAUGE_PROM_PORT_DEFAULT))
        self._gauge_prom_endpoint = f"http://{_GAUGE_PROM_HOST}:{gauge_prom_port}"

        self._initialize_orchestration()

        self._logger.info('Attaching event channel...')
        self._faucet_events = forch.faucet_event_client.FaucetEventClient(
            self._config.event_client)
        self._local_collector.initialize()
        self._cpn_collector.initialize()
        self._logger.info('Using peer controller %s', self._get_peer_controller_url())

        if str(self._config.proxy_server):
            self._varz_proxy = ForchProxy(self._config.proxy_server, content_type='text/plain')
            self._varz_proxy.start()

        self._validate_config_files()

        varz_retry = 10
        while varz_retry > 0:
            time.sleep(10)
            try:
                self._get_varz_config()
                break
            except Exception as e:
                self._logger.error('Waiting for varz config: %s', e)
                varz_retry -= 1

        if varz_retry == 0:
            raise MetricsFetchingError('Could not get Faucet varz metrics')

        self._register_handlers()
        self._start()
        self._initialized = True

    def _initialize_orchestration(self):
        if self._should_enable_faucetizer:
            self._initialize_faucetizer()
            self._faucetizer.reload_structural_config()

            if self._gauge_config_file:
                self._faucetizer.reload_and_flush_gauge_config(self._gauge_config_file)
            if self._segments_vlans_file:
                self._faucetizer.reload_segments_to_vlans(self._segments_vlans_file)

        sequester_segment, grpc_server_port = self._calculate_sequester_config()
        if sequester_segment:
            self._device_report_server = DeviceReportServer(
                self._handle_device_result, grpc_server_port)
            self._faucet_collector.set_device_state_reporter(self._device_report_server)

        self._port_state_manager = PortStateManager(
            self._faucetizer, self, self._device_report_server,
            self._config.orchestration.sequester_config.segment)

        self._attempt_authenticator_initialise()
        self._process_static_device_placement()
        self._process_static_device_behavior()
        if self._faucetizer:
            self._faucetizer.flush_behavioral_config(force=True)

    def _attempt_authenticator_initialise(self):
        orch_config = self._config.orchestration
        if not orch_config.HasField('auth_config'):
            return
        self._logger.info('Initializing authenticator')
        self._authenticator = Authenticator(orch_config.auth_config,
                                            self._handle_auth_result,
                                            metrics=self._metrics)

    def _process_static_device_placement(self):
        placement_file_name = self._config.orchestration.static_device_placement
        if not placement_file_name:
            return
        placement_file_path = os.path.join(self._forch_config_dir, placement_file_name)
        self._reload_static_device_placement(placement_file_path)
        self._config_file_watcher.register_file_callback(
            placement_file_path, self._reload_static_device_placement)

    def _reload_static_device_placement(self, file_path):
        if self._faucetizer:
            self._faucetizer.clear_static_placements()
        devices_state = yaml_proto(file_path, DevicesState)
        for eth_src, device_placement in devices_state.device_mac_placements.items():
            self._process_device_placement(eth_src, device_placement, static=True)

    def _process_static_device_behavior(self):
        behaviors_file_name = self._config.orchestration.static_device_behavior
        if not behaviors_file_name:
            return
        behaviors_file_path = os.path.join(self._forch_config_dir, behaviors_file_name)
        self._reload_static_device_behavior(behaviors_file_path)
        self._config_file_watcher.register_file_callback(
            behaviors_file_path, self._reload_static_device_behavior)

    def _reload_static_device_behavior(self, file_path):
        self._port_state_manager.clear_static_device_behaviors()

        try:
            devices_state = yaml_proto(file_path, DevicesState)
        except Exception as error:
            msg = f'Authentication disabled: could not load static behavior file {file_path}'
            self._logger.error('%s: %s', msg, error)
            with self._states_lock:
                self._config_errors[STATIC_BEHAVIORAL_FILE] = msg
                self._should_ignore_auth_result = True
            return

        with self._states_lock:
            self._config_errors.pop(STATIC_BEHAVIORAL_FILE, None)
            self._should_ignore_auth_result = False

        self._logger.info('Authentication resumed')

        for mac, device_behavior in devices_state.device_mac_behaviors.items():
            self._port_state_manager.handle_static_device_behavior(mac, device_behavior)

    def _handle_device_result(self, device_result):
        self._port_state_manager.handle_testing_result(device_result)

    def update_device_state_varz(self, mac, state):
        if self._metrics:
            self._metrics.update_var('device_state', state, labels=[mac])

    def update_static_vlan_varz(self, mac, vlan):
        if self._metrics:
            self._metrics.update_var('static_mac_vlan', labels=[mac], value=vlan)

    def _calculate_orchestration_config(self):
        orch_config = self._config.orchestration

        self._forch_config_dir = os.getenv('FORCH_CONFIG_DIR', _FORCH_CONFIG_DIR_DEFAULT)
        self._faucet_config_dir = os.getenv('FAUCET_CONFIG_DIR', _FAUCET_CONFIG_DIR_DEFAULT)

        behavioral_config_file = (orch_config.behavioral_config_file or
                                  os.getenv('FAUCET_CONFIG_FILE') or
                                  _BEHAVIORAL_CONFIG_DEFAULT)
        self._behavioral_config_file = os.path.join(
            self._faucet_config_dir, behavioral_config_file)

        gauge_config_file = orch_config.gauge_config_file
        if gauge_config_file:
            self._gauge_config_file = os.path.join(self._forch_config_dir, gauge_config_file)

        structural_config_file = orch_config.structural_config_file
        if not structural_config_file:
            return False

        self._structural_config_file = os.path.join(
            self._forch_config_dir, structural_config_file)

        if not os.path.exists(self._structural_config_file):
            raise Exception(
                f'Structural config file does not exist: {self._structural_config_file}')

        self._segments_vlans_file = os.path.join(
            self._forch_config_dir, orch_config.segments_vlans_file)
        if not os.path.exists(self._segments_vlans_file):
            error_msg = (
                f'DVA disabled due to missing segments-to-vlans file: {self._segments_vlans_file}')
            self._config_errors[SEGMENTS_VLANS_FILE] = error_msg
            self._logger.error(error_msg)
            return False

        if not orch_config.tail_acl:
            error_msg = 'Missing tail_acl configuration for enabling DVA'
            self._config_errors[TAIL_ACL_CONFIG] = error_msg
            self._logger.error(error_msg)
            return False

        return True

    def _calculate_sequester_config(self):
        sequester_config = self._config.orchestration.sequester_config
        segment = sequester_config.segment
        grpc_server_port = sequester_config.grpc_server_port
        return segment, grpc_server_port

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

        self._config_file_watcher = FileChangeWatcher(
            os.path.dirname(self._structural_config_file))

        self._faucetizer = faucetizer.Faucetizer(
            orch_config, self._structural_config_file, self._behavioral_config_file, self)

        if orch_config.faucetize_interval_sec:
            self._faucetize_scheduler = HeartbeatScheduler(orch_config.faucetize_interval_sec)

            update_write_faucet_config = (lambda: (
                self._faucetizer.reload_structural_config(),
                self._faucetizer.flush_behavioral_config(force=True)))
            self._faucetize_scheduler.add_callback(update_write_faucet_config)
        else:
            self._config_file_watcher.register_file_callback(
                self._structural_config_file, self._faucetizer.reload_structural_config)
            if self._gauge_config_file:
                self._config_file_watcher.register_file_callback(
                    self._gauge_config_file, self._faucetizer.reload_and_flush_gauge_config)

        if self._segments_vlans_file:
            self._config_file_watcher.register_file_callback(
                self._segments_vlans_file, self._faucetizer.reload_segments_to_vlans)

    def _initialize_gauge_metrics_scheduler(self, interval_sec):
        get_gauge_metrics = (
            lambda target_metrics:
            self._varz_collector.retry_get_metrics(self._gauge_prom_endpoint, target_metrics))
        heartbeat_update_packet_count = functools.partial(
            self._faucet_collector.heartbeat_update_packet_count,
            interval=interval_sec, get_metrics=get_gauge_metrics)
        self._gauge_metrics_scheduler = HeartbeatScheduler(interval_sec=interval_sec)
        self._gauge_metrics_scheduler.add_callback(heartbeat_update_packet_count)

    def reregister_include_file_watchers(self, old_include_files, new_include_files):
        """reregister the include file watchers"""
        self._config_file_watcher.unregister_file_callbacks(old_include_files)
        for new_include_file in new_include_files:
            self._config_file_watcher.register_file_callback(
                new_include_file, self._faucetizer.reload_include_file)

    def _process_device_placement(self, eth_src, device_placement, static=False):
        """Call device placement API for faucetizer/authenticator"""
        propagate_placement, mac, stale_mac = self._port_state_manager.handle_device_placement(
            eth_src, device_placement, static)

        src_mac = mac if mac else eth_src

        if self._authenticator and propagate_placement:
            if stale_mac:
                self._authenticator.process_device_placement(
                    stale_mac, DevicePlacement(connected=False))
            self._authenticator.process_device_placement(src_mac, device_placement)
        else:
            self._logger.info(
                'Ignored deauthentication for port %s on switch %s',
                device_placement.port, device_placement.switch)

    def _handle_auth_result(self, mac, access, segment, role):
        self._faucet_collector.update_radius_result(mac, access, segment, role)
        with self._states_lock:
            if self._should_ignore_auth_result:
                self._logger.warning('Ingoring authentication result for device %s', mac)
            else:
                device_behavior = DeviceBehavior(segment=segment, role=role)
                self._port_state_manager.handle_device_behavior(mac, device_behavior)

    def _register_handlers(self):
        fcoll = self._faucet_collector
        handlers = [
            (FaucetEvent.ConfigChange, self._process_config_change),
            (FaucetEvent.DpChange, lambda event: fcoll.process_dp_change(
                event.timestamp, event.dp_name, None, event.reason == "cold_start")),
            (FaucetEvent.LagChange, lambda event: fcoll.process_lag_state(
                event.timestamp, event.dp_name, event.port_no, event.role, event.state)),
            (FaucetEvent.StackState, lambda event: fcoll.process_stack_state(
                event.timestamp, event.dp_name, event.port, event.state)),
            (FaucetEvent.StackTopoChange, fcoll.process_stack_topo_change_event),
            (FaucetEvent.PortChange, fcoll.process_port_change),
            (FaucetEvent.L2Learn, lambda event: fcoll.process_port_learn(
                event.timestamp, event.dp_name, event.port_no, event.eth_src, event.vid,
                event.l3_src_ip)),
            (FaucetEvent.L2Expire, lambda event: fcoll.process_port_expire(
                event.timestamp, event.dp_name, event.port_no, event.eth_src, event.vid)),
        ]

        self._faucet_events.register_handlers(handlers)

    def _get_varz_config(self):
        metrics = self._varz_collector.retry_get_metrics(
            self._faucet_prom_endpoint, _TARGET_FAUCET_METRICS)
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
        config_info, faucet_dps, behavioral_config = self._get_faucet_config()
        self._behavioral_config = behavioral_config
        self._update_config_warning_varz()

        if config_hash != config_info['hashes']:
            self._logger.warning('Config hash does not match')
        self._last_received_faucet_config_hash = config_hash

        self._faucet_collector.process_dataplane_config_change(timestamp, faucet_dps)

    def _process_config_change(self, event):
        self._faucet_collector.process_dp_config_change(
            event.timestamp, event.dp_name, event.restart_type, event.dp_id)
        if event.config_hash_info.hashes:
            self._restore_faucet_config(event.timestamp, event.config_hash_info.hashes)

    def _verify_config_hash(self):
        with self._timer_lock:
            if not self._last_faucet_config_writing_time:
                return

            elapsed_time = time.time() - self._last_faucet_config_writing_time
            if elapsed_time < self._config_hash_verification_timeout_sec:
                return

            config_info, _, _ = self._get_faucet_config()
            if config_info['hashes'] != self._last_received_faucet_config_hash:
                raise Exception(f'Config hash does not match after '
                                f'{self._config_hash_verification_timeout_sec} seconds')

            self._last_faucet_config_writing_time = None

    def reset_faucet_config_writing_time(self):
        """reset faucet config writing time"""
        with self._timer_lock:
            self._last_faucet_config_writing_time = time.time()

    def _faucet_events_connect(self):
        self._logger.info('Attempting faucet event sock connection...')
        time.sleep(1)
        try:
            self._faucet_events.connect()
            self._restore_states()
            self._faucet_collector.set_state_restored(True)
        except Exception as e:
            self._logger.error("Cannot restore states or connect to faucet", exc_info=True)
            self._faucet_collector.set_state_restored(False, e)

    def main_loop(self):
        """Main event processing loop"""
        if not self._initialized:
            self._logger.warning('Not properly initialized')
            return False

        self._logger.info('Entering main event loop...')
        try:
            while self._faucet_events:
                while not self._faucet_events.event_socket_connected:
                    self._faucet_events_connect()

                try:
                    self._faucet_events.next_event(blocking=True)
                except FaucetEventOrderError as e:
                    self._logger.error("Faucet event order error: %s", e)
                    if self._metrics:
                        self._metrics.inc_var('faucet_event_out_of_sequence_count')
                    self._restore_states()
        except KeyboardInterrupt:
            self._logger.info('Keyboard interrupt. Exiting.')
            self._faucet_events.disconnect()
        except Exception as e:
            self._logger.error("Exception found in main loop: %s", e)
            raise
        return True

    def _start(self):
        """Start forchestrator components"""
        if self._faucetize_scheduler:
            self._faucetize_scheduler.start()
        if self._config_file_watcher:
            self._config_file_watcher.start()
        if self._faucet_state_scheduler:
            self._faucet_state_scheduler.start()
        if self._gauge_metrics_scheduler:
            self._gauge_metrics_scheduler.start()
        if self._metrics:
            self._metrics.update_var('forch_version', {'version': __version__})
        if self._device_report_server:
            self._device_report_server.start()

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
        if self._varz_proxy:
            self._varz_proxy.stop()
        if self._device_report_server:
            self._device_report_server.stop()

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
        self._logger.info('Local controller is at %s on %s', info[0], info[1])
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
        system_state.config_summary.CopyFrom(self._faucet_config_summary)
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
            self._logger.info('system_state_change_count sources: %s', change_counts)
            system_state.system_state_change_count = sum(change_counts)
            system_state.system_state_last_change = max(last_changes)
            system_state.system_state_last_update = max(last_updates)
        except Exception as e:
            system_state.system_state = State.broken
            system_state.system_state_detail = str(e)
            self._logger.exception(e)

    def _get_combined_summary(self, summary):
        controller_state, controller_state_detail = self._get_controller_state()
        if controller_state != State.active:
            return controller_state, controller_state_detail

        has_error = False
        has_warning = False
        details = []
        detail = ''
        for field, subsystem in summary.ListFields():
            state = subsystem.state
            if state in (State.down, State.broken):
                has_error = True
                details.append(field.name)
            elif state != State.healthy:
                has_warning = True
                details.append(field.name)
        if details:
            detail += 'broken subsystems: ' + ', '.join(details)

        if not self._faucet_events.event_socket_connected:
            has_error = True
            detail += '. Faucet disconnected'

        with self._states_lock:
            for errors in (self._config_errors, self._system_errors):
                if errors:
                    has_error = True
                    detail += '. ' + '. '.join(errors.values())

        if not detail:
            detail = 'n/a'

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

        cpn_state = self._cpn_collector.get_cpn_state()
        peer_controller = self._get_peer_controller_name()

        if peer_controller in cpn_state.cpn_nodes:
            peer_controller_state = cpn_state.cpn_nodes[peer_controller].state
        else:
            self._logger.error('Cannot get peer controller state for %s', peer_controller)
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
            new_conf_hashes, _, new_dps, top_conf = config_parser.dp_parser(
                self._behavioral_config_file, 'fconfig')
            config_hash_info = self._get_faucet_config_hash_info(new_conf_hashes)
            self._faucet_config_summary = SystemState.ConfigSummary()
            for file_name, file_hash in new_conf_hashes.items():
                self._logger.info('Loaded conf %s as %s', file_name, file_hash)
                self._faucet_config_summary.hashes[file_name] = file_hash
            for warning, message in self._validate_config(top_conf):
                self._logger.warning('Config warning %s: %s', warning, message)
                self._faucet_config_summary.warnings[warning] = message
            return config_hash_info, new_dps, top_conf
        except Exception as e:
            self._logger.error('Cannot read faucet config: %s', e)
            raise

    def _validate_config(self, config):
        warnings = []
        faucet_dp_macs = set()
        for dp_name, dp_obj in config['dps'].items():
            if 'interface_ranges' in dp_obj:
                raise Exception(
                    'Forch does not support parameter \'interface_ranges\' in faucet config')
            if 'faucet_dp_mac' not in dp_obj:
                warnings.append((dp_name, 'faucet_dp_mac not defined'))
            else:
                faucet_dp_macs.add(dp_obj['faucet_dp_mac'])
            for if_name, if_obj in dp_obj['interfaces'].items():
                if_key = '%s:%02d' % (dp_name, int(if_name))
                is_egress = 1 if 'lacp' in if_obj else 0
                is_stack = 1 if 'stack' in if_obj else 0
                is_access = 1 if 'native_vlan' in if_obj else 0
                is_tap = 1 if if_obj['description'] == 'tap' else 0
                is_mirror = 1 if if_obj['description'] == 'mirror' else 0
                if (is_egress + is_stack + is_access + is_tap + is_mirror) != 1:
                    warnings.append((if_key, 'misconfigured interface config: %d %d %d %d %d' %
                                     (is_egress, is_stack, is_access, is_tap, is_mirror)))
                if 'loop_protect_external' in if_obj:
                    warnings.append((if_key, 'deprecated loop_protect_external'))
                if is_access and 'max_hosts' not in if_obj:
                    warnings.append((if_key, 'missing recommended max_hosts'))

            if len(faucet_dp_macs) > 1:
                warnings.append(('faucet_dp_mac', 'faucet_dp_mac for DPs are not identical'))
        return warnings

    def _update_config_warning_varz(self):
        self._metrics.update_var(
            'faucet_config_warning_count', len(self._faucet_config_summary.warnings))
        for warning_key, warning_msg in self._faucet_config_summary.warnings.items():
            self._metrics.update_var('faucet_config_warning', 1, [warning_key, warning_msg])

    def _populate_versions(self, versions):
        versions.forch = __version__
        try:
            versions.faucet = os.popen('faucet --version').read().strip().split()[1]
        except Exception as e:
            versions.faucet = f'Cannot get faucet version: {e}'

    def _get_ryu_config(self):
        metrics = self._varz_collector.retry_get_metrics(
            self._faucet_prom_endpoint, _TARGET_FAUCET_METRICS)
        if 'ryu_config' not in metrics or not metrics['ryu_config'].samples:
            return {
                'warnings': 'Ryu config is missing'
            }

        ryu_config = {}
        for sample in metrics['ryu_config'].samples:
            param = sample.labels['param']
            value = sample.value
            ryu_config[param] = value

        return ryu_config

    def cleanup(self):
        """Clean up relevant internal data in all collectors"""
        self._faucet_collector.cleanup()

    def handle_active_state(self, active_state, error=None):
        """Handler for local state collector to handle controller active state"""
        with self._active_state_lock:
            self._active_state = active_state
            if error:
                self._system_errors[ACTIVE_STATE] = error
            else:
                self._system_errors.pop(ACTIVE_STATE, None)

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
            assert self._behavioral_config, 'behavioral config not initialized'
            faucet_config_map = {
                'behavioral': self._behavioral_config,
                'warnings': dict(self._faucet_config_summary.warnings)
            }
            reply = {
                'faucet': faucet_config_map,
                'forch': proto_dict(self._config),
                'ryu': self._get_ryu_config()
            }
            if self._faucetizer:
                reply['faucet']['structural'] = self._faucetizer.get_structural_config()
            return self._augment_state_reply(reply, path)
        except Exception as e:
            return f"Cannot read faucet config: {e}"
