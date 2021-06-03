"""Server to handle incoming session requests"""

import threading
import grpc

from forch.proto.shared_constants_pb2 import PortBehavior
from forch.proto.devices_state_pb2 import DevicesState
from forch.base_classes import DeviceStateReporter
from forch.utils import get_logger

try:
    from daq.proto.session_server_pb2 import SessionParams, SessionResult
    from daq.proto.session_server_pb2_grpc import SessionServerStub

    PORT_BEHAVIOR_SESSION_RESULT = {
        SessionResult.ResultCode.PENDING: PortBehavior.unknown,
        SessionResult.ResultCode.ERROR: PortBehavior.unknown,
        SessionResult.ResultCode.STARTED: PortBehavior.authenticated,
        SessionResult.ResultCode.PASSED: PortBehavior.passed,
        SessionResult.ResultCode.FAILED: PortBehavior.failed
    }
except ImportError as e:
    pass


DEFAULT_SERVER_ADDRESS = '127.0.0.1'
DEFAULT_SERVER_PORT = 50051


class DeviceReportClient(DeviceStateReporter):
    """gRPC client to send device result"""

    def __init__(self, result_handler, server_address, server_port, unauth_vlan):
        self._logger = get_logger('devreport')
        self._logger.info('Initializing with unauthenticated vlan %s', unauth_vlan)
        address = server_address or DEFAULT_SERVER_ADDRESS
        port = server_port or DEFAULT_SERVER_PORT
        target = f'{address}:{port}'
        self._logger.info('Using target server %s', target)
        channel = grpc.insecure_channel(target)
        self._stub = SessionServerStub(channel)
        self._dp_mac_map = {}
        self._mac_sessions = {}
        self._mac_device_vlan_map = {}
        self._mac_assigned_vlan_map = {}
        self._unauth_vlan = unauth_vlan
        self._lock = threading.Lock()
        self._result_handler = result_handler

    def start(self):
        """Start the client handler"""

    def stop(self):
        """Stop client handler"""

    def _connect(self, mac, vlan, assigned):
        self._logger.info('Connecting %s to %s/%s', mac, vlan, assigned)
        session_params = SessionParams()
        session_params.device_mac = mac
        session_params.device_vlan = vlan
        session_params.assigned_vlan = assigned
        session = self._stub.StartSession(session_params)
        thread = threading.Thread(target=lambda: self._process_progress(mac, session))
        thread.start()
        return session

    def disconnect(self, mac):
        with self._lock:
            session = self._mac_sessions.get(mac)
            if session:
                session.cancel()
                self._mac_sessions.pop(mac)
                self._logger.info('Device %s disconnected', mac)
            else:
                self._logger.warning('Attempt to disconnect unconnected device %s', mac)

    def _dp_key(self, dp_name, port):
        return '%s:%s' % (dp_name, port)

    def _convert_and_handle(self, mac, progress):
        result_code = progress.result.code
        if result_code:
            result_name = SessionResult.ResultCode.Name(result_code)
            self._logger.info('Device report %s as %s', mac, result_name)
            assert not progress.endpoint.ip, 'endpoint.ip and result.code defined'
            port_behavior = PORT_BEHAVIOR_SESSION_RESULT[result_code]
            devices_state = DevicesState()
            devices_state.device_mac_behaviors[mac].port_behavior = port_behavior
            return self._result_handler(devices_state)
        return False

    def _process_progress(self, mac, session):
        should_retry = True
        try:
            for progress in session:
                should_retry = False
                if self._convert_and_handle(mac, progress):
                    self._logger.warning('Terminal state reached for %s', mac)
            self._logger.error('Progress complete for %s', mac)
        except Exception as e:
            self._logger.error('Progress exception: %s', e)
        self.disconnect(mac)
        if should_retry:
            self._logger.warning('Retrying connection for %s', mac)
            self._process_session_ready(mac)

    def _process_session_ready(self, mac):
        if mac in self._mac_sessions:
            self._logger.info('Ignoring b/c existing session %s', mac)
            return
        device_vlan = self._mac_device_vlan_map.get(mac)
        assigned_vlan = self._mac_assigned_vlan_map.get(mac)
        self._logger.info('Device %s ready on %s/%s', mac, device_vlan, assigned_vlan)

        if device_vlan and assigned_vlan and device_vlan != self._unauth_vlan:
            self._mac_sessions[mac] = self._connect(mac, device_vlan, assigned_vlan)

    def process_port_state(self, dp_name, port, state):
        """Process faucet port state events"""
        mac = self._dp_mac_map.get(self._dp_key(dp_name, port))
        if mac:
            self._logger.info('Device %s port state %s', mac, state)
            if not state:
                self.disconnect(mac)

    def process_port_learn(self, dp_name, port, mac, vlan):
        """Process faucet port learn events"""
        with self._lock:
            dp_key = self._dp_key(dp_name, port)
            self._mac_device_vlan_map[mac] = vlan
            self._dp_mac_map[dp_key] = mac
            self._process_session_ready(mac)

    def process_port_assign(self, mac, vlan):
        """Process faucet port vlan assignment"""
        with self._lock:
            self._mac_assigned_vlan_map[mac] = vlan
            self._process_session_ready(mac)
