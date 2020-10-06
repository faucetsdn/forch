"""Module that manages the testing states of the access ports"""

import threading

from forch.utils import get_logger

from forch.proto.shared_constants_pb2 import DeviceEvent
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
            DeviceEvent.cleared: OPERATIONAL,
            DeviceEvent.sequestered: SEQUESTERED,
        },
        SEQUESTERED: {
            DeviceEvent.passed: OPERATIONAL,
            DeviceEvent.failed: INFRACTED,
        },
        OPERATIONAL: {
            DeviceEvent.cleared: OPERATIONAL,
        },
    }

    def __init__(self, mac, initial_state, sequester_state_callback, operational_state_callback):
        self._mac = mac
        self._current_state = initial_state
        self._sequester_state_callback = sequester_state_callback
        self._operational_state_callback = operational_state_callback

    def handle_device_event(self, device_event):
        """Handle testing state event"""
        next_state = self.TRANSITIONS.get(self._current_state, {}).get(device_event, {})

        if not next_state:
            LOGGER.warning(
                'Cannot find next state for device %s in state %s for device event %s',
                self._mac, self._current_state, device_event)
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
        self._static_device_events = {}
        self._static_device_behaviors = {}
        self._dynamic_device_behaviors = {}
        self._process_device_behavior = process_device_behavior
        self._testing_segment = testing_segment
        self._lock = threading.RLock()

    def handle_static_device_behavior(self, mac, device_behavior):
        """Add static testing state for a device"""
        with self._lock:
            static_device_event = device_behavior.device_event
            if static_device_event:
                self._static_device_events[mac] = static_device_event

            if device_behavior.segment:
                self.handle_device_behavior(mac, device_behavior, static=True)

    def handle_device_behavior(self, mac, device_behavior, static=False):
        """Handle authentication result"""
        if device_behavior.segment:
            self._handle_authenticated_device(mac, device_behavior, static)
        else:
            self._handle_unauthenticated_device(mac, static)

    def _handle_authenticated_device(self, mac, device_behavior, static):
        """Initialize or update the state machine for an authenticated device"""
        with self._lock:
            device_behaviors = (
                self._static_device_behaviors if static else self._dynamic_device_behaviors)
            device_behaviors.setdefault(mac, DeviceBehavior()).CopyFrom(device_behavior)

            static_device_event = self._static_device_events.get(mac)
            if not self._testing_segment or static_device_event == DeviceEvent.cleared:
                device_event = DeviceEvent.cleared
            else:
                device_event = DeviceEvent.sequestered

            new_state_machine = PortStateMachine(
                mac, PortStateMachine.AUTHENTICATED, self._set_port_sequestered,
                self._set_port_operational)
            state_machine = self._state_machines.setdefault(mac, new_state_machine)
            state_machine.handle_device_event(device_event)

    def _handle_unauthenticated_device(self, mac, static):
        """Handle an unauthenticated device"""
        with self._lock:
            try:
                device_behaviors = (
                    self._static_device_behaviors if static else self._dynamic_device_behaviors)
                device_behaviors.pop(mac)

                if static or mac not in self._static_device_behaviors:
                    self._state_machines.pop(mac)
                    self._process_device_behavior(mac, DeviceBehavior(), static=static)
            except KeyError as error:
                LOGGER.warning('MAC %s does not exist: %s', mac, error)

    def handle_testing_result(self, testing_result):
        """Update the state machine for a device according to the testing result"""
        for mac, device_behavior in testing_result:
            self._handle_device_event(mac, device_behavior.device_event)

    def _handle_device_event(self, mac, device_event):
        with self._lock:
            state_machine = self._state_machines.get(mac)
            if not state_machine:
                LOGGER.error(
                    'No state machine defined for device %s before receiving testing result', mac)
                return
            state_machine.handle_device_event(device_event)

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
        with self._lock:
            macs = list(self._static_device_behaviors.keys())
            for mac in macs:
                self._handle_unauthenticated_device(mac, static=True)
