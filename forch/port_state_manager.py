"""Module that manages the testing states of the access ports"""

import threading
from datetime import datetime, timedelta
import dateutil.parser
import dateutil.tz

from forch.utils import get_logger

from forch.proto.shared_constants_pb2 import PortBehavior, DVAState, TestResult
from forch.proto.devices_state_pb2 import DeviceBehavior, DevicePlacement

INVALID_VLAN = 0

STATE_HANDLERS = {}


def _register_state_handler(state_name):
    def register(func):
        STATE_HANDLERS[state_name] = func
        return func
    return register


class PortStateMachine:

    """State machine class that manages testing states of an access port"""

    UNAUTHENTICATED = DVAState.State.unauthenticated
    SEQUESTERED = DVAState.State.sequestered
    OPERATIONAL = DVAState.State.operational
    INFRACTED = DVAState.State.infracted

    # pylint: disable=no-member
    _transitions = {
        UNAUTHENTICATED: {
            PortBehavior.Behavior: {
                PortBehavior.Behavior.cleared: OPERATIONAL,
                PortBehavior.Behavior.sequestered: SEQUESTERED,
            }
        },
        SEQUESTERED: {
            PortBehavior.Behavior: {
                PortBehavior.Behavior.deauthenticated: UNAUTHENTICATED
            },
            TestResult.ResultCode: {
                TestResult.ResultCode.PASSED: OPERATIONAL,
                TestResult.ResultCode.FAILED: INFRACTED,
            }
        },
        OPERATIONAL: {
            PortBehavior.Behavior: {
                PortBehavior.Behavior.cleared: OPERATIONAL,
                PortBehavior.Behavior.deauthenticated: UNAUTHENTICATED,
                PortBehavior.Behavior.manual_sequestered: SEQUESTERED
            }
        },
    }

    class StateCallbacks:
        """Wrapper for state machine callbacks"""
        unauthenticated_state = None
        sequester_state = None
        operational_state = None
        infracted_state = None

    # pylint: disable=too-many-arguments
    def __init__(self, mac, initial_state, state_callbacks: StateCallbacks, state_overwrites=None):
        self._mac = mac
        self._current_state = initial_state
        self._state_callbacks = state_callbacks
        self._logger = get_logger('portsm')
        if state_overwrites:
            self._transitions = self._resolve_transitions(state_overwrites)
        self._handle_current_state()

    def handle_port_behavior(self, port_behavior):
        """Handle port behavior"""
        self._transition(port_behavior, PortBehavior.Behavior)

    def handle_session_result(self, session_result):
        """Handle session result"""
        self._transition(session_result, TestResult.ResultCode)

    def get_current_state(self):
        """Get current state of the port"""
        return self._current_state

    def _transition(self, event, event_type):
        next_state = self._transitions.get(self._current_state, {}).get(event_type, {}).get(event)

        if not next_state:
            self._logger.warning(
                'Cannot find next state for device %s in state %s for event %s: %s',
                self._mac, DVAState.State.Name(self._current_state),
                event_type.DESCRIPTOR.name, event_type.Name(event))
            return

        self._logger.info(
            'Device %s is entering %s state from %s state',
            self._mac, DVAState.State.Name(next_state), DVAState.State.Name(self._current_state))

        self._current_state = next_state
        self._handle_current_state()

    def _resolve_transitions(self, state_overwrites):
        def merge(original, overwrites):
            for key, value in overwrites.items():
                if isinstance(value, dict):
                    original[key] = merge(original.get(key, dict()), value)
                else:
                    original[key] = value
            return original
        return merge(self._transitions, state_overwrites)

    def _handle_current_state(self):
        if self._current_state in STATE_HANDLERS:
            STATE_HANDLERS[self._current_state](self)

    @_register_state_handler(state_name=UNAUTHENTICATED)
    def _handle_unauthenticated_state(self):
        self._logger.info('Handling unauthenticated state for device %s', self._mac)
        self._state_callbacks.unauthenticated_state(self._mac)

    @_register_state_handler(state_name=SEQUESTERED)
    def _handle_sequestered_state(self):
        self._logger.info('Handling sequestered state for device %s', self._mac)
        self._state_callbacks.sequester_state(self._mac)

    @_register_state_handler(state_name=OPERATIONAL)
    def _handle_operational_state(self):
        self._logger.info('Handling operational state for device %s', self._mac)
        self._state_callbacks.operational_state(self._mac)

    @_register_state_handler(state_name=INFRACTED)
    def _handle_infracted_state(self):
        self._logger.info('Handling infracted state for device %s', self._mac)
        self._state_callbacks.infracted_state(self._mac)


class PortStateManager:
    """Manages the states of the access ports for orchestrated testing"""
    _sequester_segment = None
    _sequester_timeout = None
    _default_auto_sequestering = PortBehavior.AutoSequestering.disabled

    # pylint: disable=too-many-arguments
    def __init__(self, device_state_manager=None, varz_updater=None,
                 device_state_reporter=None, orch_config=None):
        self._state_machines = {}
        self._auto_sequester = {}
        self._static_device_behaviors = {}
        self._dynamic_device_behaviors = {}
        self._device_state_manager = device_state_manager
        self._varz_updater = varz_updater
        self._device_state_reporter = device_state_reporter
        self._placement_to_mac = {}
        self._sequester_timer = {}
        self._scheduled_sequester_timer = {}
        self._lock = threading.RLock()
        self._logger = get_logger('portmgr')
        self._state_callbacks = self._build_state_callbacks()
        self._state_overwrites = {}
        self._orch_config = orch_config
        if orch_config and orch_config.HasField('sequester_config'):
            sequester_config = orch_config.sequester_config
            self._sequester_segment = sequester_config.sequester_segment
            self._sequester_timeout = sequester_config.sequester_timeout_sec
            self._logger.info('Configuring sequestering with segment %s, timeout %ss',
                              self._sequester_segment, self._sequester_timeout)
            if sequester_config.test_result_device_states:
                dict_maps = [(entry.test_result, entry.device_state)
                             for entry in sequester_config.test_result_device_states]
                test_result_device_states_map = dict(dict_maps)
                # pylint: disable=no-member
                self._state_overwrites = {
                    DVAState.State.sequestered: {
                        TestResult.ResultCode: test_result_device_states_map
                    }
                }
            if sequester_config.auto_sequestering:
                self._default_auto_sequestering = sequester_config.auto_sequestering

    def handle_static_device_behavior(self, mac, device_behavior):
        """Add static testing state for a device"""
        with self._lock:
            mac_lower = mac.lower()
            auto_sequester = (device_behavior.auto_sequestering
                              if device_behavior.auto_sequestering
                              else self._default_auto_sequestering)

            self._auto_sequester[mac_lower] = auto_sequester
            if device_behavior.segment:
                self.handle_device_behavior(mac_lower, device_behavior, static=True)
            scheduled_sequester = self._scheduled_sequester_timer.pop(mac_lower, None)
            if scheduled_sequester:
                scheduled_sequester.cancel()
            if device_behavior.scheduled_sequestering_timestamp:
                self._schedule_device_sequester(device_behavior, mac_lower)

    def handle_device_behavior(self, mac, device_behavior, static=False):
        """Handle authentication result"""
        mac_lower = mac.lower()
        if device_behavior.segment:
            self._handle_authenticated_device(mac_lower, device_behavior, static)
            if static:
                self._update_static_vlan_varz(
                    mac_lower, vlan=self._get_vlan_from_segment(device_behavior.segment))
        else:
            self._handle_deauthenticated_device(mac_lower, static)

    def handle_device_placement(self, mac, device_placement, static=False):
        """Handle a learning or expired VLAN for a device"""
        if device_placement.connected:
            mac_lower = mac.lower()
            return self._handle_learned_device(mac_lower, device_placement, static)

        return self._handle_disconnected_device(device_placement)

    def _build_state_callbacks(self):
        callbacks = PortStateMachine.StateCallbacks()
        callbacks.unauthenticated_state = self._handle_unauthenticated_state
        callbacks.sequester_state = self._set_port_sequestered
        callbacks.operational_state = self._set_port_operational
        callbacks.infracted_state = self._handle_infracted_state
        return callbacks

    def _schedule_device_sequester(self, device_behavior, mac):
        """Device sequestering may not occur if system is not operational"""
        try:
            parsed = dateutil.parser.parse(device_behavior.scheduled_sequestering_timestamp)
        except dateutil.parser.ParserError:
            self._logger.error("Failed to parse scheduled sequestering timestamp: %s.",
                               device_behavior.scheduled_sequestering_timestamp)
            return
        local_tz = dateutil.tz.tzlocal()
        if not parsed.tzinfo:
            parsed = parsed.replace(tzinfo=local_tz)
        if parsed >= datetime.now(local_tz):
            time_diff = parsed - datetime.now(local_tz)

            def handler():
                self._handle_scheduled_sequstering(mac)
            timer = threading.Timer(time_diff.seconds, handler)
            timer.start()
            self._scheduled_sequester_timer[mac] = timer
        else:
            self._logger.warning("Ignoring past sequester timestamp %s for device %s.",
                                 parsed, mac)

    def _handle_learned_device(self, mac, device_placement, static=False):
        old_mac = self._placement_to_mac.get((device_placement.switch, device_placement.port))
        stale_mac = old_mac if old_mac and old_mac != mac else None

        if stale_mac:
            switch = device_placement.switch
            port = device_placement.port
            self._logger.warning(
                'Cleaning stale device placement: %s, %s, %s', old_mac, switch, port)
            stale_placement = DevicePlacement(switch=switch, port=port, connected=False)
            self._handle_disconnected_device(stale_placement)

        self._placement_to_mac[(device_placement.switch, device_placement.port)] = mac
        self._process_device_placement(mac, device_placement, static=static)

        if mac not in self._state_machines:
            self._logger.info('Adding state machine %s', mac)
            self._state_machines[mac] = PortStateMachine(
                mac, PortStateMachine.UNAUTHENTICATED, self._state_callbacks,
                state_overwrites=self._state_overwrites)

            device_behavior = (self._static_device_behaviors.get(mac) or
                               self._dynamic_device_behaviors.get(mac))
            if device_behavior:
                static_behavior = mac in self._static_device_behaviors
                self.handle_device_behavior(mac, device_behavior, static=static_behavior)

        return True, None, stale_mac

    def _handle_disconnected_device(self, device_placement):
        eth_src = self._placement_to_mac.pop((device_placement.switch, device_placement.port), None)

        # Dont propagate removal of placement if not in cache
        if not eth_src:
            return False, None, None

        self._process_device_placement(eth_src, device_placement, static=False)
        if eth_src in self._state_machines:
            self._logger.info('Removing state machine %s', eth_src)
            self._state_machines.pop(eth_src)

        self._update_device_state_varz(eth_src, DVAState.initial)

        return True, eth_src, None

    def _handle_authenticated_device(self, mac, device_behavior, static):
        """Initialize or update the state machine for an authenticated device"""
        with self._lock:
            device_behaviors = (
                self._static_device_behaviors if static else self._dynamic_device_behaviors)
            device_behaviors.setdefault(mac, DeviceBehavior()).CopyFrom(device_behavior)

            auto_sequester = self._auto_sequester.get(mac, self._default_auto_sequestering)
            sequester_enabled = auto_sequester == PortBehavior.AutoSequestering.enabled
            if not self._sequester_segment or not sequester_enabled:
                port_behavior = PortBehavior.cleared
            else:
                port_behavior = PortBehavior.sequestered

            if mac in self._state_machines:
                self._state_machines[mac].handle_port_behavior(port_behavior)

    def _handle_deauthenticated_device(self, mac, static):
        """Handle an deauthenticated device"""
        with self._lock:
            device_behaviors = (
                self._static_device_behaviors if static else self._dynamic_device_behaviors)
            if mac in device_behaviors:
                device_behaviors.pop(mac)
            else:
                self._logger.warning(
                    '%s behavior does not exist for %s', 'static' if static else 'dynamic', mac)

            # ignore dynamic behavior for device that has static behavior defined
            if not static and mac in self._static_device_behaviors:
                return

            if mac in self._state_machines:
                port_behavior = PortBehavior.deauthenticated
                self._state_machines[mac].handle_port_behavior(port_behavior)
                self._process_device_behavior(mac, DeviceBehavior(), static=static)

    def handle_testing_result(self, testing_result):
        """Update the state machine for a device according to the testing result"""
        assert len(testing_result.device_mac_behaviors.items()) == 1, 'only one result allowed'
        mac, device_behavior = list(testing_result.device_mac_behaviors.items())[0]
        mac_lower = mac.lower()
        terminal = self._transition_device_state(mac_lower, device_behavior)
        if terminal and mac_lower in self._sequester_timer:
            self._logger.info('Cancelling device %s sequester timeout', mac_lower)
            self._sequester_timer[mac_lower].cancel()
            del self._sequester_timer[mac_lower]
        return terminal

    def _transition_device_state(self, mac_lower, device_behavior):
        """Process device behavior and return True if this is a terminal state"""
        # TODO: Remove this conversion when session results are being sent from DAQ
        # pylint: disable=no-member
        port_behavior = device_behavior.port_behavior
        if port_behavior == PortBehavior.Behavior.passed:
            self._handle_session_result(mac_lower, TestResult.ResultCode.PASSED)
            return True
        if port_behavior == PortBehavior.Behavior.failed:
            self._handle_session_result(mac_lower, TestResult.ResultCode.FAILED)
            return True
        if port_behavior == PortBehavior.Behavior.authenticated:
            pass
        else:
            self._logger.warning('Unknown result %s for %s',
                                 PortBehavior.Behavior.Name(port_behavior), mac_lower)
        return False

    def _handle_session_result(self, mac, session_result):
        with self._lock:
            state_machine = self._state_machines.get(mac)
            if not state_machine:
                self._logger.error(
                    'No state machine defined for device %s', mac)
                return
            state_machine.handle_session_result(session_result)

    def _handle_unauthenticated_state(self, mac):
        self._update_device_state_varz(mac, DVAState.unauthenticated)

    def _handle_scheduled_sequstering(self, mac):
        if mac in self._scheduled_sequester_timer:
            del self._scheduled_sequester_timer[mac]
        self._logger.info('Handle scheduled sequester for device %s.', mac)
        if mac in self._state_machines:
            self._state_machines[mac].handle_port_behavior(PortBehavior.manual_sequestered)

    def _handle_sequestering_timeout(self, mac):
        if mac in self._sequester_timer:
            del self._sequester_timer[mac]
        self._logger.error('Handle device %s sequester timeout after %ss.', mac,
                           self._sequester_timeout)
        # pylint: disable=no-member
        self._handle_session_result(mac, TestResult.ResultCode.FAILED)
        self._device_state_reporter.disconnect(mac)

    def _set_port_sequestered(self, mac):
        """Set port to sequester vlan"""
        operational_behavior = (
            self._static_device_behaviors.get(mac) or self._dynamic_device_behaviors.get(mac))

        device_behavior = DeviceBehavior(
            segment=self._sequester_segment, assigned_segment=operational_behavior.segment)
        self._process_device_behavior(mac, device_behavior, static=False)
        self._update_device_state_varz(mac, DVAState.sequestered)
        if self._sequester_timeout > 0:
            def handler():
                self._handle_sequestering_timeout(mac.lower())
            timeout = datetime.now() + timedelta(seconds=self._sequester_timeout)
            self._logger.info('Setting device %s sequester timeout at %s', mac, timeout)
            self._sequester_timer[mac.lower()] = threading.Timer(self._sequester_timeout, handler)
            self._sequester_timer[mac.lower()].start()

    def _set_port_operational(self, mac):
        """Set port to operation vlan"""
        static = mac in self._static_device_behaviors
        device_behavior = (
            self._static_device_behaviors.get(mac) or self._dynamic_device_behaviors.get(mac))
        assert device_behavior

        self._process_device_behavior(mac, device_behavior, static=static)
        self._update_device_state_varz(
            mac, DVAState.static_operational if static else DVAState.dynamic_operational)

    def _handle_infracted_state(self, mac):
        static = mac in self._static_device_behaviors
        self._process_device_behavior(mac, DeviceBehavior(), static=static)
        self._update_device_state_varz(mac, DVAState.infracted)

    def clear_static_device_behaviors(self):
        """Remove all static device behaviors"""
        with self._lock:
            macs = list(self._static_device_behaviors.keys())
            for mac in macs:
                self.clear_static_device_behavior(mac)

    def clear_static_device_behavior(self, mac):
        """Remove static device behaviors for mac"""
        mac = mac.lower()
        if mac not in self._static_device_behaviors:
            return
        with self._lock:
            self._update_static_vlan_varz(mac, INVALID_VLAN)
            self._handle_deauthenticated_device(mac, static=True)

    def _process_device_placement(self, mac, device_placement, static=False):
        if self._device_state_manager:
            self._device_state_manager.process_device_placement(mac, device_placement, static)

    def _process_device_behavior(self, mac, device_behavior, static=False):
        if self._device_state_manager:
            self._device_state_manager.process_device_behavior(mac, device_behavior, static)

    def _get_vlan_from_segment(self, segment):
        if self._device_state_manager:
            return self._device_state_manager.get_vlan_from_segment(segment) or INVALID_VLAN
        return INVALID_VLAN

    def _update_device_state_varz(self, mac, device_state):
        if self._varz_updater:
            self._varz_updater.update_device_state_varz(mac, device_state)

    def _update_static_vlan_varz(self, mac, vlan):
        if self._varz_updater:
            self._varz_updater.update_static_vlan_varz(mac, vlan)

    def get_dva_state(self, switch, port):
        """Return the DVA state of the device"""
        with self._lock:
            return self._get_dva_state(switch, port)

    def _get_dva_state(self, switch, port):
        mac = self._placement_to_mac.get((switch, port))
        if not mac:
            if self._orch_config and self._orch_config.unauthenticated_vlan:
                return DVAState.unauthenticated
            return DVAState.initial

        state_machine = self._state_machines.get(mac)
        if not state_machine:
            self._logger.warning('No state machine found for MAC: %s', mac)
            return DVAState.initial

        dva_state = state_machine.get_current_state()

        if dva_state == DVAState.operational:
            static = mac in self._static_device_behaviors
            return DVAState.static_operational if static else DVAState.dynamic_operational

        return dva_state
