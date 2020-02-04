"""Module for authenticating devices connecting to a faucet network"""

import logging
import sys
import os
import yaml
import collections
import argparse

from forch.forchestrator import configure_logging
from forch.radius_query import RadiusQuery
from forch.utils import proto_dict, dict_proto

from forch.proto.authentication_pb2 import AuthResult

LOGGER = logging.getLogger('authenticator')
AUTH_FILE_NAME = 'auth.yaml'


class Authenticator:
    """Authenticate devices using MAB/dot1x"""
    def __init__(self):
        self.auth_map = self._get_auth_map()

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

    def do_mab_request(self, ARGS):
        Socket = collections.namedtuple('Socket', 'listen_ip, listen_port, server_ip, server_port')
        socket_info = Socket('0.0.0.0', 0, ARGS.server_ip, ARGS.server_port)
        radius_query = RadiusQuery(socket_info, ARGS.radius_secret)
        LOGGER.info('sending MAB request')
        radius_query.send_mab_request(ARGS.src_mac, ARGS.port_id)
        radius_query.receive_radius_messages()

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
    return parser.parse_args(raw_args)

if __name__ == '__main__':
    configure_logging()
    ARGS = parse_args(sys.argv[1:])
    AUTHENTICATOR = Authenticator()
    AUTHENTICATOR.process_auth_result()
    AUTHENTICATOR.do_mab_request(ARGS)
