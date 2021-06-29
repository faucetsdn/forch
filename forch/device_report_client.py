"""Server to handle incoming session requests"""

import signal
import threading
import multiprocessing as mp

import grpc

import forch.endpoint_handler as endpoint_handler
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
except ImportError:
    PORT_BEHAVIOR_SESSION_RESULT = None


DEFAULT_SERVER_ADDRESS = '127.0.0.1'
CONNECT_TIMEOUT_SEC = 60


class DeviceReportClient(DeviceStateReporter):
    """gRPC client to send device result"""

    def __init__(self, result_handler, target, unauth_vlan, tunnel_ip):
        self._logger = get_logger('devreport')
        self._logger.info('Initializing with unauthenticated vlan %s', unauth_vlan)
        self._logger.info('Using target %s, proto %s', target, bool(PORT_BEHAVIOR_SESSION_RESULT))
        self._target = target
        self._dp_mac_map = {}
        self._mac_session_processes = {}
        self._progress_q = mp.Queue()
        self._progress_q_thread = None

        self._mac_device_vlan_map = {}
        self._mac_assigned_vlan_map = {}
        self._unauth_vlan = unauth_vlan
        self._lock = threading.Lock()
        self._result_handler = result_handler
        self._tunnel_ip = tunnel_ip
        self._endpoint_handler = endpoint_handler.EndpointHandler(tunnel_ip) if tunnel_ip else None

    def start(self):
        """Start the client handler"""
        # Context may be set already even though this function is only called once.
        try:
            mp.set_start_method('spawn')
        except RuntimeError:
            pass
        self._progress_q_thread = threading.Thread(target=self._process_progress_q)
        self._progress_q_thread.start()

    def stop(self):
        """Stop client handler"""
        self._progress_q.put((None, None))
        if self._progress_q_thread:
            self._progress_q_thread.join()

    @classmethod
    def _connect(cls, mac, vlan, assigned, target, tunnel_ip, progress_q):  # pylint: disable=too-many-arguments
        channel = grpc.insecure_channel(target)
        grpc.channel_ready_future(channel).result(timeout=CONNECT_TIMEOUT_SEC)
        stub = SessionServerStub(channel)
        session_params = SessionParams()
        session_params.device_mac = mac
        session_params.device_vlan = vlan
        session_params.assigned_vlan = assigned
        session_params.endpoint.ip = tunnel_ip
        session = stub.StartSession(session_params)
        signal.signal(signal.SIGTERM, lambda: session.cancel())
        for progress in session:
            progress_q.put((mac, progress))
        progress_q.put((mac, None))

    def disconnect(self, mac):
        with self._lock:
            process = self._mac_session_processes.get(mac)
            if process:
                process.terminate()
                self._mac_session_processes.pop(mac)
                self._logger.info('Device %s disconnected', mac)
            else:
                self._logger.warning('Attempt to disconnect unconnected device %s', mac)

    def _dp_key(self, dp_name, port):
        return '%s:%s' % (dp_name, port)

    def _convert_and_handle(self, mac, progress):
        endpoint_ip = progress.endpoint.ip
        result_code = progress.result.code
        assert not (endpoint_ip and result_code), 'both endpoint.ip and result.code defined'
        if result_code:
            result_name = SessionResult.ResultCode.Name(result_code)
            self._logger.info('Device report %s as %s', mac, result_name)
            port_behavior = PORT_BEHAVIOR_SESSION_RESULT[result_code]
            devices_state = DevicesState()
            devices_state.device_mac_behaviors[mac].port_behavior = port_behavior
            return self._result_handler(devices_state)
        if endpoint_ip:
            self._logger.info('Device report %s endpoint %s (handler=%s)',
                              mac, endpoint_ip, bool(self._endpoint_handler))
            if self._endpoint_handler:
                self._endpoint_handler.process_endpoint(progress.endpoint)
        return False

    def _process_progress_q(self):
        while True:
            mac, progress = self._progress_q.get(block=True)
            if not mac: # device client shutdown
                break
            try:
                if not progress or self._convert_and_handle(mac, progress):
                    self._logger.info('Progress complete for %s', mac)
                    self.disconnect(mac)
            except Exception as e:
                self._logger.error('Progress exception for %s: %s', mac, e)

    def _process_session_ready(self, mac):
        if mac in self._mac_session_processes:
            self._logger.info('Ignoring b/c existing session %s', mac)
            return
        device_vlan = self._mac_device_vlan_map.get(mac)
        assigned_vlan = self._mac_assigned_vlan_map.get(mac)
        self._logger.info('Device %s ready on %s/%s', mac, device_vlan, assigned_vlan)

        good_device_vlan = device_vlan and device_vlan not in (self._unauth_vlan, assigned_vlan)
        if assigned_vlan and good_device_vlan:
            self._logger.info('Connecting %s to %s/%s', mac, device_vlan, assigned_vlan)
            self._mac_session_processes[mac] = mp.Process(target=self._connect, args=(mac,
                device_vlan, assigned_vlan, self._target,
                self._tunnel_ip or DEFAULT_SERVER_ADDRESS, self._progress_q))
            self._mac_session_processes[mac].start()

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
