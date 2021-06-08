"""Simple endpoint handler for remote OVS switching fabrics.

This setup is used when the network fabric, as implemented by OVS, is not running
in the same place as forch. In this case, forch can't manipulate OVS directly,
so an instance of the endpoint handler run on the switching host to change the
vxlan configuration of the OVS setup. Architecturally, this models the world where
the vxlan tunnel originates in hardware, and has some API exposed to allow a
network controller to manipulate the hardware switches.

"""

from concurrent import futures
import logging
import subprocess
import time
import grpc

from forch.utils import get_logger

try:
    import daq.proto.session_server_pb2_grpc as server_grpc
    from daq.proto.session_server_pb2_grpc.server_grpc import SessionServerServicer
    from daq.proto.session_server_pb2 import SessionParams, SessionProgress
    PROTO_LOADED = True
except ImportError:
    PROTO_LOADED = False
    class SessionServerServicer:
        """Dummy class for weak import"""

DEFAULT_SERVER_PORT = 50111
DEFAULT_BIND_ADDRESS = '0.0.0.0'
DEFAULT_VXLAN_PORT = 4789
DEFAULT_VXLAN_VNI = 0

VXLAN_CONFIG_CMD = 'sudo ovs-vsctl set interface vxlan type=vxlan '
VXLAN_CONFIG_OPTS = 'options:remote_ip=%s options:key=%s options:dst_port=%s'

CONNECT_TIMEOUT_SEC = 60


class EndpointHandler:
    """Class to handle endpoint updates"""

    def __init__(self, target_ip):
        self._logger = get_logger('endpproxy')
        server_port = DEFAULT_SERVER_PORT
        address = f'{target_ip}:{server_port}'
        self._logger.info('Proxy requests to %s, proto %s', address, PROTO_LOADED)
        channel = grpc.insecure_channel(address)
        self._stub = server_grpc.SessionServerStub(channel)
        grpc.channel_ready_future(channel).result(timeout=CONNECT_TIMEOUT_SEC)

    def process_endpoint(self, endpoint):
        """Handle an endpoint request"""
        self._logger.info('Process request for %s', endpoint.ip)
        session_params = SessionParams()
        session_params.endpoint.CopyFrom(endpoint)
        for progress in self._stub.StartSession(session_params):
            self._logger.info('Recevied progress %s', progress)
        self._logger.info('Done with proxy request')


class EndpointServicer(SessionServerServicer):
    """gRPC servicer to receive devices state"""

    def __init__(self):
        super().__init__()
        self._logger = get_logger('endservicer')
        result = self._exec('sudo ovs-vsctl show')
        self._logger.info('result: %s', result)

    def _exec(self, cmd):
        self._logger.info('executing: %s', cmd)
        cmd_args = cmd.split(' ')
        process = subprocess.run(cmd_args, capture_output=True, check=False)
        if process.returncode:
            self._logger.warning('execution failed: %s, %s, %s',
                                 process.returncode, process.stdout, process.stderr)
            raise Exception('Failed subshell execution')
        return process.stdout.decode('utf-8')

    def _session_stream(self, request):
        yield SessionProgress()

    # pylint: disable=invalid-name
    def StartSession(self, request, context):
        """Start a session servicer"""
        endpoint = request.endpoint
        self._logger.info('Redirect tunnel to %s', endpoint.ip)
        cmd = VXLAN_CONFIG_CMD + VXLAN_CONFIG_OPTS % (
            endpoint.ip, DEFAULT_VXLAN_VNI, DEFAULT_VXLAN_PORT)
        self._exec(cmd)
        return self._session_stream(request)


class EndpointServer:
    """Endpoint configuration server"""

    def __init__(self, server_address=DEFAULT_BIND_ADDRESS, server_port=DEFAULT_SERVER_PORT):
        self._logger = get_logger('endserver')
        self._server = grpc.server(futures.ThreadPoolExecutor())
        self._servicer = EndpointServicer()

        server_grpc.add_SessionServerServicer_to_server(self._servicer, self._server)

        self._address = f'{server_address}:{server_port}'
        self._logger.info('Listening on %s', self._address)
        self._server.add_insecure_port(self._address)
        self._server.start()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    SERVER = EndpointServer()
    time.sleep(1000000000)
