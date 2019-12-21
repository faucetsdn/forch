"""Module for authenticating devices connecting to a faucet network"""

import logging
import sys
import os
import yaml

from forch.forchestrator import configure_logging
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


if __name__ == '__main__':
    configure_logging()
    AUTHENTICATOR = Authenticator()
    AUTHENTICATOR.process_auth_result()
