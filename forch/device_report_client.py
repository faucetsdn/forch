"""Server to handle incoming session requests"""

import grpc
import threading

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
        LOGGER.info('Initializing DeviceReportClient')
        address = server_address or DEFAULT_SERVER_ADDRESS
        port = server_port or DEFAULT_SERVER_PORT
        channel = grpc.insecure_channel(f'{address}:{port}')
        self._stub = SessionServerStub(channel)
        self._rpc_timeout_sec = DEFAULT_RPC_TIMEOUT_SEC
        self._dp_mac_map = {}
        self._mac_sessions = {}
        self._mac_device_vlan_map = {}
        self._mac_assigned_vlan_map = {}

    def start(self):
        """Initiate a client connection"""
        LOGGER.info('starting client')

    def stop(self):
        """Terminates all onging grpc calls"""
        LOGGER.info('stopping client')

    def _connect(self, mac, vlan, assigned):
        session_params = SessionParams()
        session_params.device_mac = mac
        session_params.device_vlan = vlan
        session_params.assigned_vlan = assigned
        progresses = self._stub.StartSession(session_params,
                                             timeout=self._rpc_timeout_sec)
        thread = threading.Thread(target=lambda : self._process_progress(mac, progresses))
        thread.start();

        return thread

    def _dp_key(self, dp_name, port):
        return '%s:%s' % (dp_name, port)

    def _process_progress(self, mac, progresses):
        LOGGER.info('waiting for progress on %s', mac)
        for progress in progresses:
            LOGGER.info('progress report for %s: %s', mac, progress.endpoint_ip)
        LOGGER.info('done with progresses')

    def process_port_state(self, dp_name, port, state):
        """Process faucet port state events"""
        dp_key = self._dp_key(dp_name, port)
        LOGGER.info('process_port_state %s %s', dp_key, state)

    def _process_session_ready(self, mac):
        device_vlan = self._mac_device_vlan_map.get(mac)
        assigned_vlan = self._mac_assigned_vlan_map.get(mac)
        LOGGER.info('device %s ready on %s/%s', mac, device_vlan, assigned_vlan)
        if device_vlan and assigned_vlan:
            assert not self._mac_sessions.get(mac), 'session already started'
            self._mac_sessions[mac] = self._connect(mac, device_vlan, assigned_vlan)

    def process_port_learn(self, dp_name, port, mac, vlan):
        """Process faucet port learn events"""
        dp_key = self._dp_key(dp_name, port)
        LOGGER.info('process_port_learn %s %s %s', dp_key, mac, vlan)
        self._mac_assigned_vlan_map[mac] = vlan
        self._dp_mac_map[dp_key] = mac
        self._process_session_ready(mac)

    def process_port_assign(self, mac, assigned):
        """Process faucet port vlan assignment"""
        LOGGER.info('process_port_assign %s %s', mac, assigned)
        self._mac_device_vlan_map[mac] = assigned
        self._process_session_ready(mac)
