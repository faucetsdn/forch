"""Module that manages the testing states of the access ports"""

import threading

from forch.utils import get_logger

from forch.proto.shared_constants_pb2 import PortBehavior
from forch.proto.devices_state_pb2 import DeviceBehavior
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
    def __init__(self, process_device_placement, process_device_behavior, get_vlan_from_segment,
                 update_device_state_varz=None, update_static_behavior_varz=None,
                 testing_segment=None):
        self._state_machines = {}
        self._static_port_behaviors = {}
        self._static_device_behaviors = {}
        self._dynamic_device_behaviors = {}
        self._process_device_placement = process_device_placement
        self._process_device_behavior = process_device_behavior
        self._get_vlan_from_segment = get_vlan_from_segment
        self._device_state_varz_callback = update_device_state_varz
        self._static_behavior_varz_callback = update_static_behavior_varz
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
                self._static_behavior_varz_callback(
                    mac, self._get_vlan_from_segment(device_behavior.segment))
        else:
            self._handle_deauthenticated_device(mac, static)

    def handle_device_placement(self, mac, device_placement, static=False, expired_vlan=None):
        """Handle a learning or expired VLAN for a device"""
        if device_placement.connected:
            # if device is learned
            if self._process_device_placement:
                self._process_device_placement(mac, device_placement, static=static)

            if mac not in self._state_machines:
                self._state_machines[mac] = PortStateMachine(
                    mac, PortStateMachine.UNAUTHENTICATED, self._handle_unauthenticated_state,
                    self._set_port_sequestered, self._set_port_operational,
                    self._handle_infracted_state)

                device_behavior = (self._static_device_behaviors.get(mac) or
                                   self._dynamic_device_behaviors.get(mac))
                if device_behavior:
                    static = mac in self._static_device_behaviors
                    self.handle_device_behavior(mac, device_behavior, static=static)

            return True

        # if device vlan is expired
        static_behavior = self._static_device_behaviors.get(mac)
        dynamic_behavior = self._dynamic_device_behaviors.get(mac)
        device_behavior = static_behavior or dynamic_behavior
        if device_behavior and self._get_vlan_from_segment:
            port_vlan = self._get_vlan_from_segment(device_behavior.segment)
        else:
            port_vlan = None

        if expired_vlan and port_vlan != expired_vlan:
            return False

        if self._process_device_placement:
            self._process_device_placement(mac, device_placement, static=False)
        if mac in self._state_machines:
            self._state_machines.pop(mac)

        self._update_device_state_varz(mac, DVAState.initial)

        return True

    def _handle_authenticated_device(self, mac, device_behavior, static):
        """Initialize or update the state machine for an authenticated device"""
        if not self._process_device_behavior:
            return

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
        if not self._process_device_behavior:
            return

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
        if not self._process_device_behavior:
            return
        device_behavior = DeviceBehavior(segment=self._testing_segment)
        self._process_device_behavior(mac, device_behavior, static=False)
        self._update_device_state_varz(mac, DVAState.sequestered)

    def _set_port_operational(self, mac):
        """Set port to operation vlan"""
        if not self._process_device_behavior:
            return
        device_behavior = (
            self._static_device_behaviors.get(mac) or self._dynamic_device_behaviors.get(mac))
        static = mac in self._static_device_behaviors
        assert device_behavior
        self._process_device_behavior(mac, device_behavior, static=static)
        self._update_device_state_varz(mac, DVAState.static if static else DVAState.operational)

    def _handle_infracted_state(self, mac):
        self._update_device_state_varz(mac, DVAState.infracted)

    def _update_device_state_varz(self, mac, device_state):
        if self._device_state_varz_callback:
            self._device_state_varz_callback(mac, device_state)

    def clear_static_device_behaviors(self):
        """Remove all static device behaviors"""
        with self._lock:
            macs = list(self._static_device_behaviors.keys())
            for mac in macs:
                self._static_behavior_varz_callback(mac, vlan=INVALID_VLAN)
                self._handle_deauthenticated_device(mac, static=True)
