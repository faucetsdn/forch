"""Module that implements MAB state machine"""""

import logging
from threading import Timer

LOGGER = logging.getLogger('mabsm')


class MacAuthBypassStateMachine():
    """Class represents the MAB state machine that handles the MAB for a session"""""


    def __init__(self, src_mac, port_id, radius_query_callback, auth_callback):
        self.src_mac = src_mac
        self.port_id = port_id
        self.auth_callback = auth_callback
        self.radius_query_callback = radius_query_callback

    def get_state(self):
        """Return current state"""
        return self.current_state.name

    def process_trigger(self, trigger):
        """Process trigger"""
        pass

    def host_learnt(self):
        """Host learn event"""
        LOGGER.info('Anurag host_learnt %s', self.src_mac)
        self.radius_query_callback(self.src_mac, self.port_id)

    def host_expired(self):
        """Host expired"""
        self.process_trigger(self.EXPIRE)

    def received_radius_accept(self, segment, role):
        """Received RADIUS accept message"""
        LOGGER.info('Anurag received_radius_accept %s %s %s', self.src_mac, segment, role)
        self.auth_callback(self.src_mac, segment, role)

    def received_radius_reject(self):
        """Received RADIUS reject message"""
        LOGGER.info('Anurag received_radius_reject %s', self.src_mac)
        self.auth_callback(self.src_mac)
