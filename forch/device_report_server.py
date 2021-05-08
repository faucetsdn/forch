"""gRPC server to receive devices state"""

from concurrent import futures
from queue import Queue
import threading
import grpc

from forch.base_classes import DeviceStateReporter
from forch.utils import get_logger

import forch.proto.grpc.device_report_pb2_grpc as device_report_pb2_grpc
from forch.proto.shared_constants_pb2 import Empty, PortBehavior
from forch.proto.devices_state_pb2 import DevicePortEvent

DEFAULT_ADDRESS = '0.0.0.0'
DEFAULT_PORT = 50051
DEFAULT_MAX_WORKERS = 10


class DeviceEntry:
    """Utility class for device entries"""

    mac = None
    vlan = None
    assigned = None
    port_up = None


class DeviceReportServicer(device_report_pb2_grpc.DeviceReportServicer):
    """gRPC servicer to receive devices state"""

    def __init__(self, on_receiving_result):
        super().__init__()
        self._on_receiving_result = on_receiving_result
        self._logger = get_logger('drserver')
        self._port_device_mapping = {}
        self._port_events_listeners = {}
        self._mac_assignments = {}
        self._lock = threading.Lock()

    def _get_port_event(self, device):
        port_state = PortBehavior.PortState.up if device.port_up else PortBehavior.PortState.down
        return DevicePortEvent(state=port_state, device_vlan=device.vlan,
                               assigned_vlan=device.assigned)

    def _get_device(self, mac_addr):
        for device in self._port_device_mapping.values():
            if device.mac == mac_addr:
                return device
        return None

    def _send_device_port_event(self, device):
        if not device or device.mac not in self._port_events_listeners:
            return
        port_event = self._get_port_event(device)
        self._logger.info('Sending %d DevicePortEvent %s %s %s %s',
                          len(self._port_events_listeners[device.mac]), device.mac,
                          # pylint: disable=no-member
                          port_event.state, device.vlan, device.assigned)
        for queue in self._port_events_listeners[device.mac]:
            queue.put(port_event)

    def process_port_state(self, dp_name, port, state):
        """Process faucet port state events"""
        with self._lock:
            device = self._port_device_mapping.setdefault((dp_name, port), DeviceEntry())
        device.port_up = state
        if not state:
            device.assigned = None
            device.vlan = None
        self._send_device_port_event(device)

    def process_port_learn(self, dp_name, port, mac, vlan):
        """Process faucet port learn events"""
        with self._lock:
            device = self._port_device_mapping.setdefault((dp_name, port), DeviceEntry())
        device.mac = mac
        device.vlan = vlan
        device.port_up = True
        device.assigned = self._mac_assignments.get(mac)
        self._send_device_port_event(device)

    def process_port_assign(self, mac, assigned):
        """Process assigning a device to a vlan"""
        self._mac_assignments[mac] = assigned
        with self._lock:
            for mapping in self._port_device_mapping:
                device = self._port_device_mapping.get(mapping)
                if device.mac == mac:
                    device.assigned = assigned
                    if not assigned:
                        device.vlan = None
                        device.port_up = False
                    self._send_device_port_event(device)
                    return

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
        self._logger.info('Attaching response channel for device %s', request.mac)
        self._port_events_listeners.setdefault(request.mac, []).append(listener_q)
        device = self._get_device(request.mac)
        if device:
            yield self._get_port_event(device)
        while True:
            item = listener_q.get()
            if item is False:
                break
            yield item
        self._port_events_listeners[request.mac].remove(listener_q)


class DeviceReportServer(DeviceStateReporter):
    """Devices state server"""

    def __init__(self, on_receiving_result, address=None, port=None, max_workers=None):
        self._server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=max_workers or DEFAULT_MAX_WORKERS))

        self._servicer = DeviceReportServicer(on_receiving_result)
        device_report_pb2_grpc.add_DeviceReportServicer_to_server(self._servicer, self._server)

        server_address_port = f'{address or DEFAULT_ADDRESS}:{port or DEFAULT_PORT}'
        self._server.add_insecure_port(server_address_port)

    def disconnect(self, mac):
        """Process a port disconnect"""
        self._servicer.process_port_assign(mac, None)

    def process_port_state(self, dp_name, port, state):
        """Process faucet port state events"""
        self._servicer.process_port_state(dp_name, port, state)

    def process_port_learn(self, dp_name, port, mac, vlan):
        """Process faucet port learn events"""
        self._servicer.process_port_learn(dp_name, port, mac, vlan)

    def process_port_assign(self, mac, vlan):
        """Process faucet port vlan assignment"""
        self._servicer.process_port_assign(mac, vlan)

    def start(self):
        """Start the server"""
        self._server.start()

    def stop(self):
        """Stop the server"""
        self._server.stop(grace=None)
