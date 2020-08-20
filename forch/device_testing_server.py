"""gRPC server to receive device testing result"""

from concurrent import futures
import grpc
import logging

import forch.proto.device_testing_pb2_grpc as device_testing_pb2_grpc

LOGGER = logging.getLogger('cstate')
ADDRESS_DEFAULT = '0.0.0.0'
PORT_DEFAULT = 50051
MAX_WORKERS_DEFAULT = 10


class DeviceTestingServicer(device_testing_pb2_grpc.DeviceTestingServicer):
    """gRPC servicer to receive device testing result"""

    def __init__(self, on_receiving_result):
        self._on_receiving_result = on_receiving_result

    def ReportTestingResult(self, request, context):
        if not request:
            LOGGER.warning('Received empty request for gRPC ReportTestingResult')
            return

        self._on_receiving_result(request)

        LOGGER.info(
            'Received testing result for device %s: passed: %s', request.mac, request.passed)


class DeviceTestingServer:
    """Device testing server"""

    def __init__(self, on_receiving_result, address=None, port=None, max_workers=None):
        self._server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=max_workers or MAX_WORKERS_DEFAULT))

        servicer = DeviceTestingServer(on_receiving_result)
        device_testing_pb2_grpc.add_DeviceTestingServicer_to_server(servicer, self._server)

        server_address_port = f'{address or ADDRESS_DEFAULT}:{port or PORT_DEFAULT}'
        self._server.add_insecure_port(server_address_port)

    def start(self):
        """Start device testing server"""
        self._server.start()

    def stop(self):
        """Stop device testing server"""
        self._server.stop()
