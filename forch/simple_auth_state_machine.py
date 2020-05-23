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
    QUERY_TIMEOUT_SEC = 10
    REJECT_TIMEOUT_SEC = 300
    AUTH_TIMEOUT_SEC = 3600

    # pylint: disable=too-many-arguments
    def __init__(self, src_mac, port_id, auth_config,
                 radius_query_callback, auth_callback, metrics=None):
        self.src_mac = src_mac
        self.port_id = port_id
        self._auth_callback = auth_callback
        self._radius_query_callback = radius_query_callback
        self._current_state = None
        self._retry_backoff = 0
        self._current_timeout = 0
        self._max_radius_backoff = auth_config.max_radius_backoff or self.MAX_RADIUS_BACKOFF
        self._query_timeout_sec = auth_config.query_timeout_sec or self.QUERY_TIMEOUT_SEC
        self._rej_timeout_sec = auth_config.reject_timeout_sec or self.REJECT_TIMEOUT_SEC
        self._auth_timeout_sec = auth_config.auth_timeout_sec or self.AUTH_TIMEOUT_SEC
        self._metrics = metrics
        self._transition_lock = Lock()
        self._reset_state_machine()

    def _increment_retries(self):
        self._retry_backoff += 1

    def _state_transition(self, target, expected=None):
        if expected is not None:
            message = 'state was %s expected %s' % (self._current_state, expected)
            assert self._current_state == expected, message
        LOGGER.debug('Transition for %s: %s -> %s', self.src_mac, self._current_state, target)
        self._current_state = target

    def _reset_state_machine(self):
        self._state_transition(self.UNAUTH)
        self._retry_backoff = 0
        self._current_timeout = time.time() + self._rej_timeout_sec

    def get_state(self):
        """Return current state"""
        return self._current_state

    def process_trigger(self, trigger):
        """Process trigger"""

    def host_learned(self):
        """Host learn event"""
        with self._transition_lock:
            if self._current_state != self.UNAUTH:
                self._reset_state_machine()
            self._state_transition(self.REQUEST, self.UNAUTH)
            self._radius_query_callback(self.src_mac, self.port_id)
            backoff = min(self._retry_backoff, self._max_radius_backoff)
            backoff_time = backoff * self._query_timeout_sec
            self._current_timeout = time.time() + backoff_time

    def host_expired(self):
        """Host expired"""
        with self._transition_lock:
            self._reset_state_machine()
            self._auth_callback(self.src_mac, self.UNAUTH, None, None)

    def received_radius_accept(self, segment, role):
        """Received RADIUS accept message"""
        with self._transition_lock:
            if self._current_state != self.REQUEST:
                LOGGER.warning('Unexpected RADIUS response for %s, Ignoring it.', self.src_mac)
                return
            self._state_transition(self.ACCEPT, self.REQUEST)
            self._current_timeout = time.time() + self._auth_timeout_sec
            self._retry_backoff = 0
            self._auth_callback(self.src_mac, self.ACCEPT, segment, role)

    def received_radius_reject(self):
        """Received RADIUS reject message"""
        with self._transition_lock:
            if self._current_state != self.REQUEST:
                LOGGER.warning('Unexpected RADIUS response for %s, Ignoring it.', self.src_mac)
                return
            self._state_transition(self.UNAUTH, self.REQUEST)
            self._current_timeout = time.time() + self._rej_timeout_sec
            self._retry_backoff = 0
            self._auth_callback(self.src_mac, self.UNAUTH, None, None)

    def handle_sm_timer(self):
        """Handle timer timeout and check.trigger timeout behavior of states"""
        with self._transition_lock:
            if time.time() > self._current_timeout:
                if self._retry_backoff:
                    LOGGER.debug('Retrying RADIUS request for src_mac %s. Retry #%s',
                                 self.src_mac, self._retry_backoff)
                self._radius_query_callback(self.src_mac, self.port_id)
                backoff = min(self._retry_backoff, self._max_radius_backoff)
                backoff_time = backoff * self._query_timeout_sec
                self._current_timeout = time.time() + backoff_time
                if self._current_state == self.REQUEST:
                    if self._metrics:
                        self._metrics.inc_var('radius_query_timeouts')
                    self._increment_retries()
                    LOGGER.debug('RADIUS request timed out for %s', self.src_mac)
                else:
                    self._state_transition(self.REQUEST)
                    self._auth_callback(self.src_mac, self.UNAUTH, None, None)
