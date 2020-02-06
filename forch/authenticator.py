"""Module for authenticating devices connecting to a faucet network"""

import logging
import sys
import os
import collections
import argparse
import yaml
from threading import RLock

from forch.forchestrator import configure_logging
from forch.radius_query import RadiusQuery
from forch.utils import proto_dict, dict_proto

from forch.proto.authentication_pb2 import AuthResult

LOGGER = logging.getLogger('authenticator')
AUTH_FILE_NAME = 'auth.yaml'


class Authenticator:
    """Authenticate devices using MAB/dot1x"""
    def __init__(self, radius_ip=None, radius_port=None, radius_secret=None):
        self.auth_map = self._get_auth_map()
        self.radius_query = None
        if radius_ip and radius_port and radius_secret:
            Socket = collections.namedtuple('Socket', 'listen_ip, listen_port, server_ip, server_port')
            socket_info = Socket('0.0.0.0', 0, self.radius_ip, self.radius_port)
            self.radius_query = RadiusQuery(socket_info, self.radius_secret)
            self.radius_query.lock = Rlock()

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
        """Prints Authi example object to out"""
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

    def do_mab_request(self, _args):
        """Initiate MAB request"""
        Socket = collections.namedtuple('Socket', 'listen_ip, listen_port, server_ip, server_port')
        socket_info = Socket('0.0.0.0', 0, _args.server_ip, _args.server_port)
        radius_query = RadiusQuery(socket_info, _args.radius_secret)
        LOGGER.info('sending MAB request')
        radius_query.send_mab_request(_args.src_mac, _args.port_id)
        radius_query.receive_radius_messages()

    def process_device_placement(eth_src, device_placement):
        """Process device placement info and initiate mab query"""


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
    AUTHENTICATOR = Authenticator()
    AUTHENTICATOR.process_auth_result()
    if ARGS.mab:
        AUTHENTICATOR.do_mab_request(ARGS)
