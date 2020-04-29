"""Handle the RADIUS socket
"""
import socket
import logging
from threading import RLock

LOGGER = logging.getLogger('rsocket')


class RadiusSocket:
    """Handle the RADIUS socket"""

    def __init__(self, source_ip, source_port, server_ip,  # pylint: disable=too-many-arguments
                 server_port):
        self.socket = None
        self.source_ip = source_ip
        self.source_port = source_port
        self.server_ip = server_ip
        self.server_port = server_port
        self.lock = RLock()

    def setup(self):
        """Setup RADIUS Socket"""
        LOGGER.info("Setting up radius socket.")
        try:
            self.socket = socket.socket(socket.AF_INET,
                                        socket.SOCK_DGRAM)
            self.socket.bind((self.source_ip, self.source_port))
        except socket.error as err:
            LOGGER.error("Unable to setup socket: %s", str(err))
            raise err

    def send(self, data):
        """Sends on the radius socket
            data (bytes): what to send"""
        with self.lock:
            self.socket.sendto(data, (self.server_ip, self.server_port))

    def receive(self):
        """Receives from the radius socket"""
        return self.socket.recv(4096)
