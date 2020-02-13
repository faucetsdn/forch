from transitions import State, Machine
from transitions.extensions.states import add_state_features, Timeout
import logging


@add_state_features(Timeout)
class TimeoutStateMachine(Machine):
        pass


class MacAuthBypassStateMachine():
    """Class represents the MAB state machine that handles the MAB for a session"""

    RADIUS_RETRIES = 3
    RADIUS_RESPONSE_TIMEOUT = 300
    RADIUS_SESSION_TIMEOUT = 3600

    UNAUTH = "Unauthorized"
    REQUEST = "Request sent"
    IDLE = "Waiting RADIUS response"
    ACCEPT = "Session authorized by RADIUS"

    states = [
        {'name': UNAUTH, 'on_enter': '_reset_retries'},
        {'name': REQUEST, 'on_enter': '_send_mab_request'},
        {'name': IDLE, 'timeout': RADIUS_RESPONSE_TIMEOUT,
         'on_timeout': '_radius_timeout'},
        {'name': ACCEPT,
         'timeout': RADIUS_SESSION_TIMEOUT,
         'on_timeout': '_auth_session_timeout'}
    ]

    transitions = [
        {'trigger': 'host_learnt', 'source': UNAUTH, 'dest': REQUEST},
        {'trigger': '_sent_mab_request', 'source': REQUEST, 'dest': IDLE},
        {'trigger': 'received_radius_accept', 'source': IDLE, 'dest': ACCEPT},
        {'trigger': 'received_radius_reject', 'source': IDLE, 'dest': UNAUTH},
        {'trigger': '_radius_timeout', 'source': IDLE, 'dest': REQUEST, 'unless': '_too_many_retries', 'after': '_increment_retries'},
        {'trigger': '_radius_timeout', 'source': IDLE, 'dest': UNAUTH, 'conditions': '_too_many_retries'},
        {'trigger': '_auth_session_timeout', 'source': ACCEPT, 'dest':UNAUTH},
        {'trigger': 'host_expired', 'source': '*', 'dest': UNAUTH}
    ]

    def __init__(self, request_callback,
                 retries=RADIUS_RETRIES,
                 resp_timeout=RADIUS_RESPONSE_TIMEOUT,
                 session_timeout=RADIUS_SESSION_TIMEOUT):
        self._max_radius_retries = retries
        self._response_timeout = resp_timeout
        self._session_timeout = session_timeout
        self._request_callback = request_callback

        self._retries = 0

        self._machine = TimeoutStateMachine(model=self, states=MacAuthBypassStateMachine.states, transitions=MacAuthBypassStateMachine.transitions, initial=MacAuthBypassStateMachine.UNAUTH, queued=True)
        self._machine.get_state(MacAuthBypassStateMachine.IDLE).timeout = self._response_timeout
        self._machine.get_state(MacAuthBypassStateMachine.ACCEPT).timeout = self._session_timeout

        logging.basicConfig(level=logging.INFO)
        logging.getLogger('transitions').setLevel(logging.INFO)

    def _reset_retries(self):
        self._retries = 0

    def _send_mab_request(self):
        self._request_callback()
        self._sent_mab_request()

    def _too_many_retries(self):
        return self._retries >= self._max_radius_retries

    def _increment_retries(self):
        self._retries += 1

    def get_state(self):
        return self.state
