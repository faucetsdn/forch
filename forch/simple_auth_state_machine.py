"""
Module that implements MAB state machine

There are three authentication states for a device:

UNAUTH:  unauthenticated state
REQUEST: RADIUS request is sent on behalf of this device and no response is received yet
ACCEPT:  device is authenticated by the RADIUS server
"""

from threading import Lock
import time

from forch.utils import get_logger


class AuthStateMachine():
    """Class represents the state machine that handles the Auth for a session"""""

    UNAUTH = "Unauthorized"
    REQUEST = "RADIUS Request"
    ACCEPT = "Authorized"
    MAX_RADIUS_RETRIES = 5
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
        self._radius_retries = 0
        self._current_timeout = 0
        self._max_radius_retries = auth_config.max_radius_retries or self.MAX_RADIUS_RETRIES
        self._query_timeout_sec = auth_config.query_timeout_sec or self.QUERY_TIMEOUT_SEC
        self._rej_timeout_sec = auth_config.reject_timeout_sec or self.REJECT_TIMEOUT_SEC
        self._auth_timeout_sec = auth_config.auth_timeout_sec or self.AUTH_TIMEOUT_SEC
        self._metrics = metrics
        self._transition_lock = Lock()
        self._logger = get_logger('mabsm')

        self._reset_state_machine()

    def _increment_radius_retries(self):
        self._radius_retries += 1

    def _calculate_backoff_sec(self):
        return self._radius_retries * self._query_timeout_sec

    def _state_transition(self, target, expected=None):
        if expected is not None:
            message = 'state was %s expected %s' % (self._current_state, expected)
            assert self._current_state == expected, message
        self._logger.debug('Transition for %s: %s -> %s', self.src_mac, self._current_state, target)
        self._current_state = target

    def _reset_state_machine(self):
        self._state_transition(self.UNAUTH)
        self._radius_retries = 0
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
            self._current_timeout = time.time() + self._calculate_backoff_sec()

    def host_expired(self):
        """Host expired"""
        with self._transition_lock:
            self._reset_state_machine()
            self._auth_callback(self.src_mac, self.UNAUTH, None, None)

    def received_radius_accept(self, segment, role):
        """Received RADIUS accept message"""
        with self._transition_lock:
            if self._current_state != self.REQUEST:
                self._logger.warning(
                    'Unexpected RADIUS response for %s, Ignoring it.', self.src_mac)
                return
            self._state_transition(self.ACCEPT, self.REQUEST)
            self._current_timeout = time.time() + self._auth_timeout_sec
            self._radius_retries = 0
            self._auth_callback(self.src_mac, self.ACCEPT, segment, role)

    def received_radius_reject(self):
        """Received RADIUS reject message"""
        with self._transition_lock:
            if self._current_state != self.REQUEST:
                self._logger.warning(
                    'Unexpected RADIUS response for %s, Ignoring it.', self.src_mac)
                return
            self._reset_state_machine()
            self._auth_callback(self.src_mac, self.UNAUTH, None, None)

    def handle_sm_timer(self):
        """
        Handle timer timeout behavior of states:
        * REQUEST: request timeout & retries < max_retries  => REQUEST + send request
        * REQUEST: request timeout & retries == max_retries => UNAUTH  + deauthenticate
        * ACCEPT:  auth timeout => REQUEST + send request
        * UNAUTH:  any timeout  => REQUEST + send request
        * Unknown: any timeout  => UNAUTH  + deauthenticate
        """
        with self._transition_lock:
            if time.time() > self._current_timeout:
                if self._current_state == self.REQUEST:
                    self._logger.error('RADIUS request timed out for %s', self.src_mac)
                    if self._radius_retries:
                        if self._radius_retries < self._max_radius_retries:
                            self._increment_radius_retries()
                            self._resend_radius_request()
                        else:
                            self._reset_state_machine()
                            self._auth_callback(self.src_mac, self.UNAUTH, None, None)
                    if self._metrics:
                        self._metrics.inc_var('radius_query_timeouts')
                elif self._current_state == self.ACCEPT or self._current_state == self.UNAUTH:
                    self._state_transition(self.REQUEST)
                    self._resend_radius_request()
                else:
                    self._logger.error(
                        'Unknown auth state %s for MAC %s', self._current_state, self.src_mac)
                    self._reset_state_machine()
                    self._auth_callback(self.src_mac, self.UNAUTH, None, None)

    def _resend_radius_request(self):
        if self._radius_retries:
            self._logger.debug(
                'Retrying RADIUS request for src_mac %s. Retry #%s', self.src_mac,
                self._radius_retries)
        self._radius_query_callback(self.src_mac, self.port_id)
        self._current_timeout = time.time() + self._calculate_backoff_sec()
