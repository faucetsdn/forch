"""Module that manages the testing states of the access ports"""

import threading

from forch.utils import get_logger

from forch.proto.shared_constants_pb2 import PortBehavior
from forch.proto.devices_state_pb2 import DeviceBehavior


LOGGER = get_logger('portsm')
STATE_HANDLERS = {}


def _register_state_handler(state_name):
    def register(func):
        STATE_HANDLERS[state_name] = func
        return func
    return register


class PortStateMachine:
    """State machine class that manages testing states of an access port"""

    AUTHENTICATED = 'authenticated'
    SEQUESTERED = 'sequestered'
    OPERATIONAL = 'operational'
    INFRACTED = 'infracted'

    TRANSITIONS = {
        AUTHENTICATED: {
            PortBehavior.cleared: OPERATIONAL,
            PortBehavior.sequestered: SEQUESTERED,
        },
        SEQUESTERED: {
            PortBehavior.passed: OPERATIONAL,
            PortBehavior.failed: INFRACTED,
        },
        OPERATIONAL: {
            PortBehavior.cleared: OPERATIONAL,
        },
    }

    def __init__(self, mac, initial_state, sequester_state_callback, operational_state_callback):
        self._mac = mac
        self._current_state = initial_state
        self._sequester_state_callback = sequester_state_callback
        self._operational_state_callback = operational_state_callback

    def handle_port_behavior(self, port_behavior):
        """Handle testing state event"""
        next_state = self.TRANSITIONS.get(self._current_state, {}).get(port_behavior, {})

        if not next_state:
            LOGGER.warning(
                'Cannot find next state for device %s in state %s for port behavior %s',
                self._mac, self._current_state, port_behavior)
            return

        LOGGER.info(
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

    @_register_state_handler(state_name=AUTHENTICATED)
    def _handle_authenticated_state(self):
        LOGGER.info('Handling authenticated state for device %s', self._mac)

    @_register_state_handler(state_name=SEQUESTERED)
    def _handle_sequestered_state(self):
        LOGGER.info('Handling sequestered state for device %s', self._mac)
        self._sequester_state_callback(self._mac)

    @_register_state_handler(state_name=OPERATIONAL)
    def _handle_operational_state(self):
        LOGGER.info('Handling operational state for device %s', self._mac)
        self._operational_state_callback(self._mac)


class PortStateManager:
    """Manages the states of the access ports for orchestrated testing"""
    def __init__(self, process_device_behavior, testing_segment=None):
        self._state_machines = {}
        self._static_port_behaviors = {}
        self._static_device_behaviors = {}
        self._dynamic_device_behaviors = {}
        self._process_device_behavior = process_device_behavior
        self._testing_segment = testing_segment
        self._lock = threading.Lock()

    def handle_static_device_behavior(self, mac, device_behavior):
        """Add static testing state for a device"""
        isolation_behavior = device_behavior.isolation_behavior
        if isolation_behavior:
            self._static_port_behaviors[mac] = isolation_behavior

        if device_behavior.segment:
            self.handle_device_behavior(mac, device_behavior, static=True)

    def handle_device_behavior(self, mac, device_behavior, static=False):
        """Handle authentication result"""
        if device_behavior.segment:
            self._handle_authenticated_device(mac, device_behavior, static)
        else:
            self._handle_unauthenticated_device(mac)

    def _handle_authenticated_device(self, mac, device_behavior, static=False):
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

            new_state_machine = PortStateMachine(
                mac, PortStateMachine.AUTHENTICATED, self._set_port_sequestered,
                self._set_port_operational)
            state_machine = self._state_machines.setdefault(mac, new_state_machine)
            state_machine.handle_port_behavior(port_behavior)

    def _handle_unauthenticated_device(self, mac):
        """Handle an unauthenticated device"""
        with self._lock:
            try:
                self._dynamic_device_behaviors.pop(mac)
                self._state_machines.pop(mac)
                self._process_device_behavior(mac, DeviceBehavior(), static=False)
            except KeyError as error:
                LOGGER.warning('MAC %s does not exist: %s', mac, error)

    def handle_testing_result(self, testing_result):
        """Update the state machine for a device according to the testing result"""
        with self._lock:
            state_machine = self._state_machines.get(testing_result.mac)
            if not state_machine:
                LOGGER.error(
                    'No state machine defined for device %s before receiving testing result',
                    testing_result.mac)
                return
            state_machine.handle_port_behavior(testing_result.port_behavior)

    def _set_port_sequestered(self, mac):
        """Set port to sequester vlan"""
        device_behavior = DeviceBehavior(segment=self._testing_segment)
        self._process_device_behavior(mac, device_behavior, static=False)

    def _set_port_operational(self, mac):
        """Set port to operation vlan"""
        device_behavior = (
            self._static_device_behaviors.get(mac) or self._dynamic_device_behaviors.get(mac))
        static = mac in self._static_device_behaviors
        assert device_behavior
        self._process_device_behavior(mac, device_behavior, static=static)

    def clear_static_device_behaviors(self):
        """Remove all static device behaviors"""
        self._static_device_behaviors.clear()
