"""gRPC server to receive devices state"""

from concurrent import futures
from queue import Queue
import grpc

from forch.utils import get_logger

import forch.proto.grpc.device_report_pb2_grpc as device_report_pb2_grpc
from forch.proto.shared_constants_pb2 import Empty, PortBehavior
from forch.proto.devices_state_pb2 import DevicePortEvent

ADDRESS_DEFAULT = '0.0.0.0'
PORT_DEFAULT = 50051
MAX_WORKERS_DEFAULT = 10


class DeviceReportServicer(device_report_pb2_grpc.DeviceReportServicer):
    """gRPC servicer to receive devices state"""

    def __init__(self, on_receiving_result):
        super().__init__()
        self._on_receiving_result = on_receiving_result
        self._logger = get_logger('drserver')
        self._port_device_mapping = {}
        self._port_events_listeners = {}

    def process_port_change(self, timestamp, dp_name, port, state):
        """Process faucet port state events"""
        mac = self._port_device_mapping.get((dp_name, port))
        if not mac or mac not in self._port_events_listeners:
            return
        event = PortBehavior.PortEvent.up if state else PortBehavior.PortEvent.down
        port_event = DevicePortEvent(event=event, timestamp=timestamp)
        for queue in self._port_events_listeners[mac]:
            queue.put(port_event)

    def process_port_learn(self, dp_name, port, mac):
        """Process faucet port learn events"""
        self._port_device_mapping[(dp_name, port)] = mac

    # pylint: disable=invalid-name
    def ReportDevicesState(self, request, context):
        """RPC call for client to send devices state"""
        if not request:
            self._logger.warning('Received empty request in gRPC ReportDevicesState')
            return Empty()

        self._logger.info(
            'Received DevicesState of %d devices', len(request.device_mac_behaviors))
        # Closes DevicePortEvent streams in GetPortState
        for mac in request.device_mac_behaviors.keys():
            for queue in self._port_events_listeners.get(mac, []):
                queue.put(False)
        self._on_receiving_result(request)

        return Empty()

    # pylint: disable=invalid-name
    def GetPortState(self, request, context):
        listener_q = Queue()
        self._port_events_listeners.setdefault(request.mac, []).append(listener_q)
        while True:
            item = listener_q.get()
            if item is False:
                break
            yield item

class DeviceReportServer:
    """Devices state server"""

    def __init__(self, on_receiving_result, address=None, port=None, max_workers=None):
        self._server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=max_workers or MAX_WORKERS_DEFAULT))

        self._servicer = DeviceReportServicer(on_receiving_result)
        device_report_pb2_grpc.add_DeviceReportServicer_to_server(self._servicer, self._server)

        server_address_port = f'{address or ADDRESS_DEFAULT}:{port or PORT_DEFAULT}'
        self._server.add_insecure_port(server_address_port)

    def process_port_change(self, *args):
        """Process faucet port state events"""
        self._servicer.process_port_change(*args)

    def process_port_learn(self, *args):
        """Process faucet port learn events"""
        self._servicer.process_port_learn(*args)

    def start(self):
        """Start the server"""
        self._server.start()

    def stop(self):
        """Stop the server"""
        self._server.stop(grace=None)
