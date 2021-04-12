"""Server to handle incoming session requests"""

import grpc

from forch.base_classes import DeviceStateReporter
from forch.utils import get_logger

LOGGER = get_logger('devreport')

try:
    from daq.proto.session_server_pb2 import SessionParams
    from daq.proto.session_server_pb2_grpc import SessionServerStub
    LOGGER.info('imported daq dependencies')
except ImportError as e:
    LOGGER.error('daq dependencies not found: %s', e)


DEFAULT_SERVER_ADDRESS = '127.0.0.1'
DEFAULT_SERVER_PORT = 50051
DEFAULT_RPC_TIMEOUT_SEC = 10


class DeviceReportClient(DeviceStateReporter):
    """gRPC client to send device result"""

    def __init__(self, result_handler, server_address, server_port):
        address = server_address or DEFAULT_SERVER_ADDRESS
        port = server_port or DEFAULT_SERVER_PORT
        channel = grpc.insecure_channel(f'{address}:{port}')
        self._stub = SessionServerStub(channel)
        self._rpc_timeout_sec = DEFAULT_RPC_TIMEOUT_SEC

    def start(self):
        """Initiate a client connection"""
        LOGGER.info('Starting DeviceReportClient')
        session_params = SessionParams()
        session_params.device_mac = 'devicemac'
        self._stub.StartSession(session_params,
                                timeout=self._rpc_timeout_sec)

    def stop(self):
        """Terminates all onging grpc calls"""

    def process_port_state(self, dp_name, port, state):
        """Process faucet port state events"""

    def process_port_learn(self, dp_name, port, mac, vlan):
        """Process faucet port learn events"""

    def process_port_assign(self, mac, assigned):
        """Process faucet port vlan assignment"""
