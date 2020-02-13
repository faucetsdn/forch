import logging
from threading import Timer

LOGGER = logging.getLogger('mabsm')

def log_method(method):
    """Generate method for logging"""""
    def wrapped(self, *args, **kwargs):
        """Method that gets called for logging"""
        LOGGER.debug('Entering %s' % method.__name__)
        return method(self, *args, **kwargs)
    return wrapped


class State():
    """Represents a state in the state machine"""
    def __init__(self, name, on_enter=None, on_exit=None, timeout=None, on_timeout=None):
        self.name = name
        self.on_enter = [on_enter] if on_enter and not isinstance(on_enter, list) else None
        self.on_exit = [on_exit] if on_exit and not isinstance(on_exit, list) else None
        self.on_timeout = [on_timeout] if on_timeout and not isinstance(on_timeout, list) else None
        self.timeout = timeout


    def enter_state(self):
        self.call_callbacks(self.on_enter)

        if self.timeout and self.on_timeout:
            timer = Timer(self.timeout, self.handle_timeout)
            timer.daemon = True
            timer.start()

    def call_callbacks(self, call_list):
        if call_list:
            for callback in call_list:
                callback()

    def handle_timeout(self):
        self.call_callbacks(self.on_timeout)

    def exit_state(self):
        self.call_callbacks(self.on_exit)


class MacAuthBypassStateMachine():
    """Class represents the MAB state machine that handles the MAB for a session"""


    UNAUTH = "Unauthorized"
    REQUEST = "Request sent"
    IDLE = "Waiting RADIUS response"
    ACCEPT = "Authorized"

    LEARN = "Host learnt"
    SENT_REQ = "Sent MAB request"
    RECV_ACCPT = "Received RADIUS accept"
    RECV_REJ = "Received RADIUS reject"
    REQ_TIMEOUT = "RADIUS request timeout"
    AUTH_TIMEOUT = "Auth session timed out"
    EXPIRE = "Host expired"


    def __init__(self, session):
        self._retries = 0
        self.session = session
        self.states = {}
        self._initialize_states()
        self.current_state = self.states[self.UNAUTH]

        self.transitions = [
            {'trigger': self.LEARN, 'source': self.UNAUTH, 'dest': self.REQUEST},
            {'trigger': self.SENT_REQ, 'source': self.REQUEST, 'dest': self.IDLE},
            {'trigger': self.RECV_ACCPT, 'source': self.IDLE, 'dest': self.ACCEPT},
            {'trigger': self.RECV_REJ, 'source': self.IDLE, 'dest': self.UNAUTH},
            {'trigger': self.REQ_TIMEOUT, 'source': self.IDLE, 'dest': self.REQUEST,
             'condition': self._retry_allowed, 'after': self._increment_retries},
            {'trigger': self.REQ_TIMEOUT, 'source': self.IDLE,
             'dest': self.UNAUTH, 'condition': self._too_many_retries},
            {'trigger': self.AUTH_TIMEOUT, 'source': self.ACCEPT, 'dest': self.UNAUTH},
            {'trigger': self.EXPIRE, 'source': '*', 'dest': self.UNAUTH}
        ]

    def _initialize_states(self):
        self.states[self.UNAUTH] = State(name=self.UNAUTH, on_enter=self._handle_reject)
        self.states[self.REQUEST] = State(name=self.REQUEST, on_enter=self._send_mab_request)
        self.states[self.IDLE] = State(name=self.IDLE, timeout=self.session.response_timeout,
                                       on_timeout=self._radius_timeout)
        self.states[self.ACCEPT] = State(name=self.ACCEPT, on_enter=self._handle_accept,
                                    timeout=self.session.session_timeout, on_timeout=self._auth_session_timeout)

    def _reset_state_machine(self):
        self.retries = 0
        self.current_state = self.states[self.UNAUTH]

    @log_method
    def _radius_timeout(self):
        self.process_trigger(self.REQ_TIMEOUT)

    @log_method
    def _auth_session_timeout(self):
        self.process_trigger(self.AUTH_TIMEOUT)

    @log_method
    def _handle_accept(self):
        self.session.session_result(accept=True)
        pass

    @log_method
    def _handle_reject(self):
        self.session.session_result(accept=False)
        self._reset_retries()

    @log_method
    def _reset_retries(self):
        self._retries = 0

    @log_method
    def _send_mab_request(self):
        self.session.send_mab_request()
        self.process_trigger(self.SENT_REQ)

    def _too_many_retries(self):
        return self._retries >= self.session.max_radius_retries

    def _retry_allowed(self):
        return self._retries < self.session.max_radius_retries

    @log_method
    def _increment_retries(self):
        self._retries += 1

    def get_state(self):
        return self.current_state.name

    @log_method
    def process_trigger(self, trigger):
        for transition in self.transitions:
            if transition['trigger'] == trigger:
                if ('condition' in transition and not transition['condition']()):
                    LOGGER.debug('Conditions not met for transition from  %s to %s for %s',
                                   transition['source'], transition['dest'], transition['trigger'])
                    continue
                if self.current_state.name == transition['source'] or transition['source'] == '*':
                    self.current_state.exit_state()
                    self.current_state = self.states[transition['dest']]
                    if 'after' in transition:
                        transition['after']()
                    LOGGER.info('Transitioned from  (%s) to (%s) because (%s)',
                                transition['source'], transition['dest'], transition['trigger'])
                    self.current_state.enter_state()
                    return
        LOGGER.info('No matching transition for (%s). State machine in (%s)', trigger, self.current_state.name)

    @log_method
    def host_learnt(self):
        """Host learn event"""
        self.process_trigger(self.LEARN)

    @log_method
    def host_expired(self):
        """Host expired"""
        self.process_trigger(self.EXPIRE)

    @log_method
    def received_radius_accept(self):
        """Received RADIUS accept message"""
        self.process_trigger(self.RECV_ACCPT)

    @log_method
    def received_radius_reject(self):
        """Received RADIUS reject message"""
        self.process_trigger(self.RECV_REJ)
