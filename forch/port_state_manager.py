"""Module that manages the testing states of the access ports"""

import logging
import threading

from forch.proto.shared_constants_pb2 import PortBehavior


LOGGER = logging.getLogger('portsm')
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
    }

    def __init__(self, mac, initial_state):
        self._mac = mac
        self._current_state = initial_state

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

    @_register_state_handler(state_name=OPERATIONAL)
    def _handle_operational_state(self):
        LOGGER.info('Handling operational state for device %s', self._mac)


class PortStateManager:
    """Manages the states of the access ports for orchestrated testing"""
    def __init__(self):
        self._state_machines = {}
        self._static_port_behaviors = {}
        self._lock = threading.Lock()

    def process_static_port_behavior(self, mac, port_behavior):
        """Add static testing state for a device"""
        self._static_port_behaviors[mac] = port_behavior

    def handle_authenticated_device(self, mac):
        """initialize or update the state machine for an authenticated device"""
        with self._lock:
            state_machine = self._state_machines.setdefault(
                mac, PortStateMachine(mac, PortStateMachine.AUTHENTICATED))
            static_port_behavior = self._static_port_behaviors.get(mac)
            state_machine.handle_port_behavior(
                PortBehavior.cleared if static_port_behavior == PortBehavior.cleared
                else PortBehavior.sequestered)

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
