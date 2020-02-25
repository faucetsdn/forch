"""Module that implements MAB state machine"""""

import logging
from threading import Lock
import time

LOGGER = logging.getLogger('mabsm')


class AuthStateMachine():
    """Class represents the state machine that handles the Auth for a session"""""

    UNAUTH = "Unauthorized"
    REQUEST = "RADIUS Request"
    ACCEPT = "Authorized"
    MAX_RADIUS_BACKOFF = 5
    QUERY_STATE_TIMEOUT = 10
    REJECT_STATE_TIMEOUT = 300
    AUTH_STATE_TIMEOUT = 3600

    # pylint: disable=too-many-arguments
    def __init__(self, src_mac, port_id, auth_config, radius_query_callback, auth_callback):
        self.src_mac = src_mac
        self.port_id = port_id
        self.auth_callback = auth_callback
        self.radius_query_callback = radius_query_callback
        self.current_state = None
        self._retry_backoff = 0
        self.current_timeout = 0
        self._max_radius_backoff = auth_config.get('max_radius_backoff', self.MAX_RADIUS_BACKOFF)
        self._query_state_timeout = auth_config.get('query_state_timeout', self.QUERY_STATE_TIMEOUT)
        self._rej_state_timeout = auth_config.get('reject_state_timeout', self.REJECT_STATE_TIMEOUT)
        self._auth_state_timeout = auth_config.get('auth_state_timeout', self.AUTH_STATE_TIMEOUT)
        self.transition_lock = Lock()
        self._reset_state_machine()

    def _increment_retries(self):
        if self._retry_backoff < self._max_radius_backoff:
            self._retry_backoff += 1

    def _state_transition(self, target, expected=None):
        if expected is not None:
            message = 'state was %s expected %s' % (self.current_state, expected)
            assert self.current_state == expected, message
        LOGGER.info('Transition: %s -> %s', self.current_state, target)
        self.current_state = target

    def _reset_state_machine(self):
        self._state_transition(self.UNAUTH)
        self._retry_backoff = 0
        self.current_timeout = time.time() + self._rej_state_timeout
        self.auth_callback(self.src_mac, None, None)

    def get_state(self):
        """Return current state"""
        return self.current_state

    def process_trigger(self, trigger):
        """Process trigger"""

    def host_learned(self):
        """Host learn event"""
        with self.transition_lock:
            if self.current_state != self.UNAUTH:
                self._reset_state_machine()
            self._state_transition(self.REQUEST, self.UNAUTH)
            self.radius_query_callback(self.src_mac, self.port_id)

    def host_expired(self):
        """Host expired"""
        with self.transition_lock:
            self._reset_state_machine()

    def received_radius_accept(self, segment, role):
        """Received RADIUS accept message"""
        with self.transition_lock:
            self._state_transition(self.ACCEPT, self.REQUEST)
            self.current_timeout = time.time() + self._auth_state_timeout
            self._retry_backoff = 0
            self.auth_callback(self.src_mac, segment, role)

    def received_radius_reject(self):
        """Received RADIUS reject message"""
        with self.transition_lock:
            self._state_transition(self.UNAUTH, self.REQUEST)
            self.current_timeout = time.time() + self._rej_state_timeout
            self._retry_backoff = 0
            self.auth_callback(self.src_mac, None, None)

    def handle_sm_timer(self):
        """Handle timer timeout and check.trigger timeout behavior of states"""
        with self.transition_lock:
            if time.time() > self.current_timeout:
                self.radius_query_callback(self.src_mac, self.port_id)
                self.current_timeout = time.time() + self._retry_backoff * self._query_state_timeout
                if self.current_state == self.REQUEST:
                    self._increment_retries()
                else:
                    self._state_transition(self.REQUEST)
                    self.auth_callback(self.src_mac, None, None)
