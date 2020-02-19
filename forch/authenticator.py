"""Module for authenticating devices connecting to a faucet network"""

import logging
import sys
import os
import collections
import argparse
import threading
import yaml

from forch.heartbeat_scheduler import HeartbeatScheduler
import forch.radius_query as r_query
from forch.simple_auth_state_machine import AuthStateMachine
from forch.utils import configure_logging
from forch.utils import proto_dict, dict_proto

from forch.proto.authentication_pb2 import AuthResult

LOGGER = logging.getLogger('auth')
AUTH_FILE_NAME = 'auth.yaml'

STATE_MACHINE_TIMER_FREQ = 3

class Authenticator:
    """Authenticate devices using MAB/dot1x"""
    def __init__(self, radius_ip, radius_port, radius_secret, auth_callback=None):
        self.auth_map = self._get_auth_map()
        self.radius_query = None
        self.sessions = {}
        self.auth_callback = auth_callback
        if radius_ip and radius_port and radius_secret:
            Socket = collections.namedtuple(
                'Socket', 'listen_ip, listen_port, server_ip, server_port')
            socket_info = Socket('0.0.0.0', 0, radius_ip, radius_port)
            self.radius_query = r_query.RadiusQuery(
                socket_info, radius_secret, self.process_radius_result)
            threading.Thread(target=self.radius_query.receive_radius_messages, daemon=True).start()

        self.timer = HeartbeatScheduler(STATE_MACHINE_TIMER_FREQ)
        self.timer.add_callback(self.handle_sm_timeout)
        self.timer.start()

    def _get_auth_map(self):
        base_dir = os.getenv('FORCH_CONFIG_DIR')
        auth_file = os.path.join(base_dir, AUTH_FILE_NAME)
        auth_map = None
        with open(auth_file, 'r') as stream:
            try:
                auth_map = yaml.safe_load(stream).get('auth_map')
            except yaml.YAMLError as exc:
                LOGGER.error("Error loading yaml file: %s", exc, exc_info=True)
        return auth_map

    def authenticate(self, device_id):
        """Returns role and segment for given device_id"""
        auth_result = {}
        if device_id in self.auth_map:
            auth_result = self.auth_map.get(device_id)
        else:
            auth_result = self.auth_map.get('default')
        auth_result['device_id'] = device_id
        return dict_proto(auth_result, AuthResult)

    def process_auth_result(self):
        """Prints Auth example object to out"""
        base_dir = os.getenv('FORCH_CONFIG_DIR')
        auth_ex_file = os.path.join(base_dir, 'auth_result.yaml')
        auth_list = None
        with open(auth_ex_file, 'r') as stream:
            try:
                auth_list = yaml.safe_load(stream).get('auth_list')
            except yaml.YAMLError as exc:
                LOGGER.error("Error loading yaml file: %s", exc, exc_info=True)
        for auth_obj in auth_list:
            auth_example = dict_proto(auth_obj, AuthResult)
            sys.stdout.write(str(proto_dict(auth_example)) + '\n')

    def stop(self):
        """Stop state machine timer"""
        if self.timer:
            self.timer.stop()

    def do_mab_request(self, src_mac, port_id):
        """Initiate MAB request"""
        LOGGER.info('sending MAB request for %s', src_mac)
        self.radius_query.send_mab_request(src_mac, port_id)

    def process_device_placement(self, src_mac, device_placement):
        """Process device placement info and initiate mab query"""
        portid_hash = ((device_placement.switch + str(device_placement.port)).encode('utf-8')).hex()
        port_id = int(portid_hash[:6], 16)
        if src_mac not in self.sessions:
            self.sessions[src_mac] = AuthStateMachine(
                src_mac, port_id, self.radius_query.send_mab_request, self.process_session_result)
        if device_placement.connected:
            self.sessions[src_mac].host_learned()
        else:
            self.sessions[src_mac].host_expired()
            self.sessions.pop(src_mac)

    def process_radius_result(self, src_mac, code, segment, role):
        """Process RADIUS result from radius_query"""
        LOGGER.info("Received RADIUS result: %s for src_mac: %s", code, src_mac)
        if code == r_query.INVALID_RESP:
            LOGGER.warning("Received invalid response for src_mac: %s", src_mac)
            return
        if src_mac not in self.sessions:
            LOGGER.warning("Session doesn't exist for src_mac:%s", src_mac)
            return
        if code == r_query.ACCEPT:
            self.sessions[src_mac].received_radius_accept(segment, role)
        else:
            self.sessions[src_mac].received_radius_reject()

    def process_session_result(self, src_mac, segment=None, role=None):
        """Process session result"""
        if self.auth_callback:
            self.auth_callback(src_mac, segment, role)

    def handle_sm_timeout(self):
        """Call timeout handlers for all active session state machines"""
        for session in self.sessions.values():
            session.handle_sm_timer()


def parse_args(raw_args):
    """Parse sys args"""
    parser = argparse.ArgumentParser(prog='authenticator', description='authenticator')
    parser.add_argument('-s', '--server-ip', type=str, default='0.0.0.0',
                        help='RADIUS server ip')
    parser.add_argument('-p', '--server-port', type=int, default=1812,
                        help='Server port that freeradius is listening on')
    parser.add_argument('-r', '--radius-secret', type=str, default='SECRET',
                        help='RADIUS server secret')
    parser.add_argument('-m', '--src_mac', type=str, default='8e:00:00:00:01:02',
                        help='MAC addr to authenticate')
    parser.add_argument('-i', '--port-id', type=int, default=12345,
                        help='Unique identifier for physical port device is on')
    parser.add_argument('--mab', action='store_true')
    return parser.parse_args(raw_args)


if __name__ == '__main__':
    configure_logging()
    ARGS = parse_args(sys.argv[1:])
    AUTHENTICATOR = Authenticator(ARGS.server_ip, ARGS.server_port, ARGS.radius_secret)
    AUTHENTICATOR.process_auth_result()
    if ARGS.mab:
        AUTHENTICATOR.do_mab_request(ARGS.src_mac, ARGS.port_id)
