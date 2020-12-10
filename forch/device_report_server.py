"""gRPC server to receive devices state"""

from concurrent import futures

import grpc

from forch.utils import get_logger

import forch.proto.grpc.device_report_pb2_grpc as device_report_pb2_grpc
from forch.proto.shared_constants_pb2 import Empty

ADDRESS_DEFAULT = '0.0.0.0'
PORT_DEFAULT = 50051
MAX_WORKERS_DEFAULT = 10


class DeviceReportServicer(device_report_pb2_grpc.DeviceReportServicer):
    """gRPC servicer to receive devices state"""

    def __init__(self, on_receiving_result):
        super().__init__()
        self._on_receiving_result = on_receiving_result
        self._logger = get_logger('drserver')

    # pylint: disable=invalid-name
    def ReportDevicesState(self, request, context):
        """RPC call for client to send devices state"""
        if not request:
            self._logger.warning('Received empty request in gRPC ReportDevicesState')
            return Empty()

        self._logger.info(
            'Received DevicesState of %d devices', len(request.device_mac_behaviors))

        self._on_receiving_result(request)

        return Empty()


class DeviceReportServer:
    """Devices state server"""

    def __init__(self, on_receiving_result, address=None, port=None, max_workers=None):
        self._server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=max_workers or MAX_WORKERS_DEFAULT))

        servicer = DeviceReportServicer(on_receiving_result)
        device_report_pb2_grpc.add_DeviceReportServicer_to_server(servicer, self._server)

        server_address_port = f'{address or ADDRESS_DEFAULT}:{port or PORT_DEFAULT}'
        self._server.add_insecure_port(server_address_port)

    def start(self):
        """Start the server"""
        self._server.start()

    def stop(self):
        """Stop the server"""
        self._server.stop(grace=None)
