from transitions import State, Machine
from transitions.extensions.states import add_state_features, Timeout
import logging


@add_state_features(Timeout)
class TimeoutStateMachine(Machine):
        pass


class MacAuthBypassStateMachine():
    """Class represents the MAB state machine that handles the MAB for a session"""


    UNAUTH = "Unauthorized"
    REQUEST = "Request sent"
    IDLE = "Waiting RADIUS response"
    ACCEPT = "Session authorized by RADIUS"

    states = [
        {'name': UNAUTH, 'on_enter': '_handle_reject'},
        {'name': REQUEST, 'on_enter': '_send_mab_request'},
        {'name': IDLE, 'timeout': 60,
         'on_timeout': '_radius_timeout'},
        {'name': ACCEPT, 'on_enter': '_handle_accept',
         'timeout': 60,
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

    def __init__(self, session):
        self._retries = 0
        self.session = session
        self._machine = TimeoutStateMachine(model=self, states=MacAuthBypassStateMachine.states, transitions=MacAuthBypassStateMachine.transitions, initial=MacAuthBypassStateMachine.UNAUTH, queued=True)
        self._machine.get_state(MacAuthBypassStateMachine.IDLE).timeout = self.session.response_timeout
        self._machine.get_state(MacAuthBypassStateMachine.ACCEPT).timeout = self.session.session_timeout

        logging.basicConfig(level=logging.INFO)
        logging.getLogger('transitions').setLevel(logging.INFO)

    def _handle_accept(self):
        self.session.session_result(accept=True)

    def _handle_reject(self):
        self.session.session_result(accept=False)
        self._reset_retries()

    def _reset_retries(self):
        self._retries = 0

    def _send_mab_request(self):
        self.session.send_mab_request()
        self._sent_mab_request()

    def _too_many_retries(self):
        return self._retries >= self.session.max_radius_retries

    def _increment_retries(self):
        self._retries += 1

    def get_state(self):
        return self.state
