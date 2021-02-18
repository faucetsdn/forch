"""Module that manages the testing states of the access ports"""

import threading

from forch.utils import get_logger

from forch.proto.shared_constants_pb2 import PortBehavior
from forch.proto.devices_state_pb2 import DeviceBehavior, DevicePlacement
from forch.proto.shared_constants_pb2 import DVAState

INVALID_VLAN = 0

STATE_HANDLERS = {}


def _register_state_handler(state_name):
    def register(func):
        STATE_HANDLERS[state_name] = func
        return func
    return register


class PortStateMachine:
    """State machine class that manages testing states of an access port"""

    UNAUTHENTICATED = 'unauthenticated'
    AUTHENTICATED = 'authenticated'
    SEQUESTERED = 'sequestered'
    OPERATIONAL = 'operational'
    INFRACTED = 'infracted'

    TRANSITIONS = {
        UNAUTHENTICATED: {
            PortBehavior.cleared: OPERATIONAL,
            PortBehavior.sequestered: SEQUESTERED,
        },
        SEQUESTERED: {
            PortBehavior.passed: OPERATIONAL,
            PortBehavior.failed: INFRACTED,
            PortBehavior.deauthenticated: UNAUTHENTICATED,
        },
        OPERATIONAL: {
            PortBehavior.cleared: OPERATIONAL,
            PortBehavior.deauthenticated: UNAUTHENTICATED,
        },
    }

    # pylint: disable=too-many-arguments
    def __init__(self, mac, initial_state, unauthenticated_state_callback, sequester_state_callback,
                 operational_state_callback, infracted_state_callback):
        self._mac = mac
        self._current_state = initial_state
        self._unauthenticated_state_callback = unauthenticated_state_callback
        self._sequester_state_callback = sequester_state_callback
        self._operational_state_callback = operational_state_callback
        self._infracted_state_callback = infracted_state_callback
        self._logger = get_logger('portsm')

        self._handle_current_state()

    def handle_port_behavior(self, port_behavior):
        """Handle port behavior"""
        next_state = self.TRANSITIONS.get(self._current_state, {}).get(port_behavior, {})

        if not next_state:
            self._logger.warning(
                'Cannot find next state for device %s in state %s for port behavior %s',
                self._mac, self._current_state, port_behavior)
            return

        self._logger.info(
            'Device %s is entering %s state from %s state',
            self._mac, next_state, self._current_state)

        self._current_state = next_state
        self._handle_current_state()

    def get_current_state(self):
        """Get current state of the port"""
        return self._current_state

    def _handle_current_state(self):
        if self._current_state in STATE_HANDLERS:
            STATE_HANDLERS[self._current_state](self)

    @_register_state_handler(state_name=UNAUTHENTICATED)
    def _handle_unauthenticated_state(self):
        self._logger.info('Handling unauthenticated state for device %s', self._mac)
        self._unauthenticated_state_callback(self._mac)

    @_register_state_handler(state_name=SEQUESTERED)
    def _handle_sequestered_state(self):
        self._logger.info('Handling sequestered state for device %s', self._mac)
        self._sequester_state_callback(self._mac)

    @_register_state_handler(state_name=OPERATIONAL)
    def _handle_operational_state(self):
        self._logger.info('Handling operational state for device %s', self._mac)
        self._operational_state_callback(self._mac)

    @_register_state_handler(state_name=INFRACTED)
    def _handle_infracted_state(self):
        self._logger.info('Handling infracted state for device %s', self._mac)
        self._infracted_state_callback(self._mac)


class PortStateManager:
    """Manages the states of the access ports for orchestrated testing"""

    # pylint: disable=too-many-arguments
    def __init__(self, device_state_manager=None, varz_updater=None,
                 device_state_reporter=None, testing_segment=None):
        self._state_machines = {}
        self._static_port_behaviors = {}
        self._static_device_behaviors = {}
        self._dynamic_device_behaviors = {}
        self._device_state_manager = device_state_manager
        self._varz_updater = varz_updater
        self._device_state_reporter = device_state_reporter
        self._placement_to_mac = {}
        self._testing_segment = testing_segment
        self._lock = threading.RLock()
        self._logger = get_logger('portmgr')

    def handle_static_device_behavior(self, mac, device_behavior):
        """Add static testing state for a device"""
        with self._lock:
            static_port_behavior = device_behavior.port_behavior
            if static_port_behavior:
                self._static_port_behaviors[mac] = static_port_behavior

            if device_behavior.segment:
                self.handle_device_behavior(mac, device_behavior, static=True)

    def handle_device_behavior(self, mac, device_behavior, static=False):
        """Handle authentication result"""
        if device_behavior.segment:
            self._handle_authenticated_device(mac, device_behavior, static)
            if static:
                self._update_static_vlan_varz(
                    mac, vlan=self._get_vlan_from_segment(device_behavior.segment))
        else:
            self._handle_deauthenticated_device(mac, static)

    def handle_device_placement(self, mac, device_placement, static=False):
        """Handle a learning or expired VLAN for a device"""
        if device_placement.connected:
            return self._handle_learned_device(mac, device_placement, static)

        return self._handle_disconnected_device(device_placement)

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
            self._state_machines[mac] = PortStateMachine(
                mac, PortStateMachine.UNAUTHENTICATED, self._handle_unauthenticated_state,
                self._set_port_sequestered, self._set_port_operational,
                self._handle_infracted_state)

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
            self._state_machines.pop(eth_src)

        self._update_device_state_varz(eth_src, DVAState.initial)

        return True, eth_src, None

    def _handle_authenticated_device(self, mac, device_behavior, static):
        """Initialize or update the state machine for an authenticated device"""
        with self._lock:
            device_behaviors = (
                self._static_device_behaviors if static else self._dynamic_device_behaviors)
            device_behaviors.setdefault(mac, DeviceBehavior()).CopyFrom(device_behavior)

            static_port_behavior = self._static_port_behaviors.get(mac)
            if not self._testing_segment or static_port_behavior == PortBehavior.cleared:
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
        for mac, device_behavior in testing_result.device_mac_behaviors.items():
            self._handle_port_behavior(mac, device_behavior.port_behavior)

    def _handle_port_behavior(self, mac, port_behavior):
        with self._lock:
            state_machine = self._state_machines.get(mac)
            if not state_machine:
                self._logger.error(
                    'No state machine defined for device %s before receiving testing result', mac)
                return
            state_machine.handle_port_behavior(port_behavior)

    def _handle_unauthenticated_state(self, mac):
        self._update_device_state_varz(mac, DVAState.unauthenticated)

    def _set_port_sequestered(self, mac):
        """Set port to sequester vlan"""
        operational_behavior = (
            self._static_device_behaviors.get(mac) or self._dynamic_device_behaviors.get(mac))
        assert operational_behavior
        operational_vlan = self._get_vlan_from_segment(operational_behavior.segment)
        if self._device_state_reporter:
            self._device_state_reporter.process_port_assign(mac, operational_vlan)

        device_behavior = DeviceBehavior(segment=self._testing_segment)
        self._process_device_behavior(mac, device_behavior, static=False)
        self._update_device_state_varz(mac, DVAState.sequestered)

    def _set_port_operational(self, mac):
        """Set port to operation vlan"""
        static = mac in self._static_device_behaviors
        device_behavior = (
            self._static_device_behaviors.get(mac) or self._dynamic_device_behaviors.get(mac))
        assert device_behavior

        self._process_device_behavior(mac, device_behavior, static=static)
        self._update_device_state_varz(mac, DVAState.static if static else DVAState.operational)

    def _handle_infracted_state(self, mac):
        static = mac in self._static_device_behaviors
        self._process_device_behavior(mac, DeviceBehavior(), static=static)
        self._update_device_state_varz(mac, DVAState.infracted)

    def clear_static_device_behaviors(self):
        """Remove all static device behaviors"""
        with self._lock:
            macs = list(self._static_device_behaviors.keys())
            for mac in macs:
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
            return self._device_state_manager.get_vlan_from_segment(segment)
        return INVALID_VLAN

    def _update_device_state_varz(self, mac, device_state):
        if self._varz_updater:
            self._varz_updater.update_device_state_varz(mac, device_state)

    def _update_static_vlan_varz(self, mac, vlan):
        if self._varz_updater:
            self._varz_updater.update_static_vlan_varz(mac, vlan)
