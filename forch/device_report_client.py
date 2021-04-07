"""gRPC client to send device result"""

import grpc

from forch.forchestrator import DeviceStateReporter

from daq.proto.grpc.device_report_pb2_grpc import DeviceReportStub


DEFAULT_SERVER_ADDRESS = '127.0.0.1'
DEFAULT_SERVER_PORT = 50051
DEFAULT_RPC_TIMEOUT_SEC = 10


class DeviceReportClient(DeviceStateReporter):
    """gRPC client to send device result"""
    def __init__(self, result_handler, server_address, server_port):
        self._initialize_stub(server_address or DEFAULT_SERVER_ADDRESS,
                              server_port or DEFAULT_SERVER_PORT)

        self._rpc_timeout_sec = DEFAULT_RPC_TIMEOUT_SEC

    def _initialize_stub(self, sever_address, server_port):
        channel = grpc.insecure_channel(f'{sever_address}:{server_port}')
        self._stub = DeviceReportStub(channel)

    def start(self):
        """Start a client connection"""

    def process_port_state(self, dp_name, port, state):
        """Process faucet port state events"""

    def process_port_learn(self, dp_name, port, mac, vlan):
        """Process faucet port learn events"""

    def process_port_assign(self, mac, assigned):
        """Process faucet port vlan assignment"""

    def stop(self):
        """Terminates all onging grpc calls"""
