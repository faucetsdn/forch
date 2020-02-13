"""Module that implements MAB state machine"""

import logging
from threading import Timer

LOGGER = logging.getLogger('mabsm')


class MacAuthBypassStateMachine():
    """Class represents the MAB state machine that handles the MAB for a session"""


    def __init__(self, radius_query_callback, auth_callback):

    def get_state(self):
        """Return current state"""
        return self.current_state.name

    def process_trigger(self, trigger):
        """Process trigger"""

    def host_learnt(self):
        """Host learn event"""
        self.process_trigger(self.LEARN)

    def host_expired(self):
        """Host expired"""
        self.process_trigger(self.EXPIRE)

    def received_radius_accept(self):
        """Received RADIUS accept message"""
        self.process_trigger(self.RECV_ACCPT)

    def received_radius_reject(self):
        """Received RADIUS reject message"""
        self.process_trigger(self.RECV_REJ)

    def radius_query_callback(self):
        """Call query callback passed"""

    def radius_auth_callback(self):
        """Call auth callback"""
