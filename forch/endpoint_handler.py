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
import threading
import yaml
import grpc

from forch.utils import get_logger
import forch.proto.endpoint_server_pb2_grpc as server_grpc
from forch.proto.endpoint_server_pb2 import Endpoint
from forch.proto.shared_constants_pb2 import Empty

DEFAULT_SERVER_PORT = 50111
DEFAULT_BIND_ADDRESS = '0.0.0.0'
DEFAULT_VXLAN_PORT = 4789
BASE_T1SW_PORT = 29
VXLAN_CMD_FMT = 'ip link add %s type vxlan id %s remote %s dstport %s srcport %s %s nolearning'

# TODO: This switch value should be configurable
T1_SW1 = 'nz-kiwi-t1sw1'
CONNECT_TIMEOUT_SEC = 60
# 'TAP' description is needed by forch to append test vlans.
TAP_PORT_CONFIG = {
    'description': 'TAP',
    'tagged_vlans': [171]
}

class EndpointHandler:
    """Class to handle endpoint updates"""

    def __init__(self, target_ip, structural_config_file):
        self._logger = get_logger('endpproxy')
        self._lock = threading.RLock()
        self._mac_tap_port = {}
        self._freed_tap_ports = set()
        self._next_tap_port = BASE_T1SW_PORT
        self._structural_config_file = structural_config_file
        server_port = DEFAULT_SERVER_PORT
        address = f'{target_ip}:{server_port}'
        self._logger.info('Proxy requests to %s', address)
        channel = grpc.insecure_channel(address)
        self._stub = server_grpc.EndpointServerStub(channel)
        grpc.channel_ready_future(channel).result(timeout=CONNECT_TIMEOUT_SEC)

    def _allocate_tap_port(self, mac):
        with self._lock:
            if mac in self._mac_tap_port:
                return self._mac_tap_port[mac]
            if self._freed_tap_ports:
                tap_port = max(self._freed_tap_ports)
                self._freed_tap_ports.remove(tap_port)
            else:
                tap_port = self._next_tap_port
                self._next_tap_port += 1
            self._mac_tap_port[mac] = tap_port
            with open(self._structural_config_file, 'r') as file:
                structural_config = yaml.safe_load(file)
                structural_config['dps'][T1_SW1]['interfaces'][tap_port] = TAP_PORT_CONFIG
            with open(self._structural_config_file, 'w') as file:
                yaml.dump(structural_config, file)
            return tap_port

    def process_endpoint(self, endpoint, mac):
        """Handle an endpoint request"""
        self._logger.info('Process request for %s', endpoint.ip)
        t1sw_port = self._allocate_tap_port(mac)
        session_endpoint = Endpoint()
        session_endpoint.ip = endpoint.ip
        session_endpoint.port = endpoint.port
        session_endpoint.vni = endpoint.vni
        session_endpoint.tap_port = t1sw_port

        self._stub.ConfigureInterface(session_endpoint)
        self._logger.info('Done with proxy request')

    def _deallocate_tap_port(self, freed_port):
        with self._lock:
            self._freed_tap_ports.add(freed_port)
            with open(self._structural_config_file, 'r') as file:
                structural_config = yaml.safe_load(file)
                self._logger.info(structural_config)
                structural_config['dps'][T1_SW1]['interfaces'].pop(freed_port, None)
            with open(self._structural_config_file, 'w') as file:
                yaml.dump(structural_config, file)

    def free_endpoint(self, mac: str):
        """Cleanup endpoint resources."""
        with self._lock:
            self._logger.info('Process request to free endpoint for %s', mac)
            freed_port = self._mac_tap_port.pop(mac, None)
            if not freed_port:
                return
            self._deallocate_tap_port(freed_port)
            # Move next_tap_port counter forward if possible
            port_range = list(range(freed_port, self._next_tap_port))
            all_free = all((port in self._freed_tap_ports for port in port_range))
            if all_free:
                self._next_tap_port = freed_port
                self._freed_tap_ports -= set(port_range)
            session_endpoint = Endpoint()
            session_endpoint.tap_port = freed_port
            self._stub.CleanupInterface(session_endpoint)
            self._logger.info('Done with proxy request')


class EndpointServicer(server_grpc.EndpointServerServicer):
    """gRPC servicer to receive devices state"""

    def __init__(self):
        super().__init__()
        self._logger = get_logger('endservicer')
        result = self._exec('sudo ovs-vsctl show')
        self._logger.info('result: %s', result)

    def _exec_no_raise(self, cmd):
        try:
            self._exec(cmd)
        except Exception as e:
            self._logger.info('Ignoring exception: %s', str(e))

    def _exec(self, cmd):
        self._logger.info('executing: %s', cmd)
        cmd_args = cmd.split(' ')
        process = subprocess.run(cmd_args, capture_output=True, check=False)
        if process.returncode:
            self._logger.warning('execution failed: %s, %s, %s',
                                 process.returncode, process.stdout, process.stderr)
            raise Exception('Failed subshell execution')
        return process.stdout.decode('utf-8')

    def _remove_interface(self, interface):
        self._logger.info('Removing vxlan interface %s', interface)
        self._exec_no_raise('sudo ip link set %s down' % interface)
        self._exec_no_raise('sudo ip link del %s' % interface)
        self._exec_no_raise('sudo ovs-vsctl del-port t1sw1 %s' % interface)

    # pylint: disable=invalid-name
    def ConfigureInterface(self, request, context):
        """Start a session servicer"""
        interface = "vxlan%s" % request.tap_port
        self._remove_interface(interface)
        self._logger.info('Adding vxlan tunnel to %s', request.ip)
        self._exec('sudo ovs-vsctl add-port t1sw1 %s -- set interface %s ofport_request=%s' % (
            interface, interface, request.tap_port
        ))
        cmd = VXLAN_CMD_FMT % (interface, request.vni, request.ip,
                               DEFAULT_VXLAN_PORT, DEFAULT_VXLAN_PORT, DEFAULT_VXLAN_PORT)
        self._exec('sudo ' + cmd)
        self._exec('sudo ip link set %s up' % interface)
        return Empty()

    def CleanupInterface(self, request, context):
        """Start a session servicer"""
        interface = "vxlan%s" % request.tap_port
        self._remove_interface(interface)
        return Empty()

class EndpointServer:
    """Endpoint configuration server"""

    def __init__(self, server_address=DEFAULT_BIND_ADDRESS, server_port=DEFAULT_SERVER_PORT):
        self._logger = get_logger('endserver')
        self._server = grpc.server(futures.ThreadPoolExecutor())
        self._servicer = EndpointServicer()

        server_grpc.add_EndpointServerServicer_to_server(self._servicer, self._server)

        self._address = f'{server_address}:{server_port}'
        self._logger.info('Listening on %s', self._address)
        self._server.add_insecure_port(self._address)
        self._server.start()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    SERVER = EndpointServer()
    time.sleep(1000000000)
