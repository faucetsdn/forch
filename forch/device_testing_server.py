"""gRPC server to receive device testing result"""

from concurrent import futures
import logging

import grpc

import forch.proto.grpc.device_testing_pb2_grpc as device_testing_pb2_grpc
from forch.proto.shared_constants_pb2 import Empty

LOGGER = logging.getLogger('grpcserver')
ADDRESS_DEFAULT = '0.0.0.0'
PORT_DEFAULT = 50051
MAX_WORKERS_DEFAULT = 10


class DeviceTestingServicer(device_testing_pb2_grpc.DeviceTestingServicer):
    """gRPC servicer to receive device testing result"""

    def __init__(self, on_receiving_result):
        super().__init__()
        self._on_receiving_result = on_receiving_result

    # pylint: disable=invalid-name
    def ReportTestingState(self, request, context):
        """RPC call for client to send device testing state"""
        if not request:
            LOGGER.warning('Received empty request for gRPC ReportTestingResult')
            return Empty()

        self._on_receiving_result(request)

        LOGGER.info(
            'Received testing state: %s, %s', request.mac, request.testing_state)

        return Empty()


class DeviceTestingServer:
    """Device testing server"""

    def __init__(self, on_receiving_result, address=None, port=None, max_workers=None):
        self._server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=max_workers or MAX_WORKERS_DEFAULT))

        servicer = DeviceTestingServicer(on_receiving_result)
        device_testing_pb2_grpc.add_DeviceTestingServicer_to_server(servicer, self._server)

        server_address_port = f'{address or ADDRESS_DEFAULT}:{port or PORT_DEFAULT}'
        self._server.add_insecure_port(server_address_port)

    def start(self):
        """Start device testing server"""
        self._server.start()

    def stop(self):
        """Stop device testing server"""
        self._server.stop(grace=None)
