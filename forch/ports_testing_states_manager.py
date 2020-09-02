"""Module that manages the testing states of the access ports"""

import logging
import threading

from forch.proto.shared_constants_pb2 import TestingState


LOGGER = logging.getLogger('portsm')
STATE_HANDLERS = {}


def _register_state_handler(state_name):
    def register(func):
        STATE_HANDLERS[state_name] = func
        return func
    return register


class PortTestingStateMachine:
    """State machine class that manages testing states of an access port"""

    AUTHENTICATED = 'authenticated'
    SEQUESTERED = 'sequestered'
    OPERATIONAL = 'operational'
    INFRACTED = 'infracted'

    TRANSITIONS = {
        AUTHENTICATED: {
            TestingState.cleared: OPERATIONAL,
            TestingState.sequestered: SEQUESTERED,
        },
        SEQUESTERED: {
            TestingState.passed: OPERATIONAL,
            TestingState.failed: INFRACTED,
        },
    }

    def __init__(self, mac, initial_state):
        self._mac = mac
        self._current_state = initial_state

    def handle_testing_state_event(self, testing_state):
        """Handle testing state event"""
        to_state = self.TRANSITIONS.get(self._current_state, {}).get(testing_state, {})

        if not to_state:
            LOGGER.warning(
                'Cannot find next state for device %s in state %s for testing_state %s',
                self._mac, self._current_state, testing_state)
            return

        LOGGER.info("Device %s entering %s state", self._mac, to_state)
        self._current_state = to_state
        self._handle_current_state()

    def get_current_state(self):
        """Get current state of the port"""
        return self._current_state

    def _handle_current_state(self):
        if self._current_state in STATE_HANDLERS:
            STATE_HANDLERS[self._current_state](self)

    @_register_state_handler(state_name=AUTHENTICATED)
    def _handle_authenticated_state(self):
        LOGGER.info("Handling authenticated state")

    @_register_state_handler(state_name=SEQUESTERED)
    def _handle_sequestered_state(self):
        LOGGER.info("Handling sequestered state")

    @_register_state_handler(state_name=OPERATIONAL)
    def _handle_operational_state(self):
        LOGGER.info("Handling operational state")


class PortsTestingStatesManager:
    """Manages the testing states of the access ports"""
    def __init__(self):
        self._state_machines = {}
        self._static_testing_states = {}
        self._lock = threading.Lock()

    def process_static_testing_state(self, mac, testing_state):
        """Add static testing state for a device"""
        self._static_testing_states[mac] = testing_state

    def handle_authenticated_device(self, mac):
        """initialize or update the state machine for an authenticated device"""
        with self._lock:
            state_machine = self._state_machines.setdefault(
                mac, PortTestingStateMachine(mac, PortTestingStateMachine.AUTHENTICATED))
            static_testing_state = self._static_testing_states.get(mac)
            state_machine.handle_testing_state_event(
                TestingState.cleared if static_testing_state == TestingState.cleared
                else TestingState.sequestered)

    def handle_testing_result(self, testing_result):
        """Update the state machine for a device according to the testing result"""
        with self._lock:
            state_machine = self._state_machines.get(testing_result.mac)
            if not state_machine:
                LOGGER.error(
                    'No state machine defined for device %s before receiving testing result',
                    testing_result.mac)
                return
            state_machine.handle_testing_state_event(testing_result.testing_state)
