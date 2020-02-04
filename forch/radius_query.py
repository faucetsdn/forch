"""Talks and listens to RADIUS. Takes a packet object as input"""
from queue import Queue
import socket
import logging
from time import sleep
from forch.radius import RadiusAttributesList, RadiusAccessRequest, Radius
from forch.radius_attributes import CallingStationId, UserName, MessageAuthenticator, \
        NASPort, UserPassword
from forch.utils import MessageParseError

LOGGER = logging.getLogger('rquery')

RADIUS_HEADER_LENGTH = 1 + 1 + 2 + 16

class RadiusSocket:
    """Handle the RADIUS socket"""

    def __init__(self, listen_ip, listen_port, server_ip,  # pylint: disable=too-many-arguments
                 server_port):
        self.socket = None
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.server_ip = server_ip
        self.server_port = server_port

    def setup(self):
        """Setup RADIUS Socket"""
        LOGGER.info("Setting up radius socket.")
        try:
            self.socket = socket.socket(socket.AF_INET,
                                        socket.SOCK_DGRAM)
            self.socket.bind((self.listen_ip, self.listen_port))
        except socket.error as err:
            self.logger.error("Unable to setup socket: %s", str(err))
            raise err

    def send(self, data):
        """Sends on the radius socket
            data (bytes): what to send"""
        self.socket.sendto(data, (self.server_ip, self.server_port))

    def receive(self):
        """Receives from the radius socket"""
        return self.socket.recv(4096)

class RadiusQuery:
    """Maintains socket information and sends out and receives requests form RADIUS server"""
    def __init__(self, socket_info, radius_secret):
        self.next_radius_id = 0
        self.packet_id_to_mac = {}
        self.packet_id_to_req_authenticator = {}
        self.running = True
        self.radius_output_q = Queue()
        #TODO: Find better way to handle secret
        self.radius_secret = radius_secret
        self.radius_socket = RadiusSocket(socket_info.listen_ip, socket_info.listen_port, \
                                          socket_info.server_ip, socket_info.server_port)
        self.radius_socket.setup()
        #self.receive_radius_messages()

    def receive_radius_messages(self):
        while self.running:
            LOGGER.info("Waiting for RADIUS messages.")
            packed_message = self.radius_socket.receive()
            try:
                radius = self.decode_radius_response(packed_message)
            except MessageParseError as exception:
                LOGGER.warning("exception: %s. message: %s", packed_message, exception)
            LOGGER.info("Received RADIUS msg: %s", radius)

    def send_mab_request(self, src_mac, port_id):
        LOGGER,info("sending MAB reqest for %s", src_mac)
        req_packet = self.encode_mab_message(src_mac, port_id)
        LOGGER.info("encoded MAB message for %s", src_mac)
        self.radius_socket.send(req_packet)
        LOGGER.info("sent MAB request for %s", src_mac)

    def encode_mab_message(self, src_mac, port_id=None):
        radius_id = self.get_next_radius_pkt_id()
        req_authenticator = self.get_req_authenticator()
        self.packet_id_to_mac[radius_id] = {'src_mac': src_mac, 'port_id': port_id}
        self.packet_id_to_req_authenticator[radius_id] = req_authenticator

        attr_list = []
        mac_str = str(src_mac).replace(':', "")
        attr_list.append(UserName.create(no_dots_mac))
        attr_list.append(CallingStationId.create(str(src_mac).replace(':', '-')))

        if port_id:
            #TODO: Need to figure out if this is needed
            attr_list.append(NASPort.create(port_id))

        ciphertext = UserPassword.encrypt(self.radius_secret, req_authenticator, mac_str)
        attr_list.append(UserPassword.create(ciphertext))

        attr_list.append(MessageAuthenticator.create(
            bytes.fromhex("00000000000000000000000000000000")))

        attributes = RadiusAttributesList(attr_list)
        access_request = RadiusAccessRequest(radius_id, req_authenticator, attributes)
        LOGGER.info("encoded %s successfully", src_mac)
        return access_request.build(self.radius_secret)

    def decode_radius_response(self, packed_msg):
        return Radius.parse(packed_msg, self.secret, self.packet_id_to_req_authenticator)

    def get_next_radius_pkt_id(self):
        radius_id = self.next_radius_id
        self.next_radius_id = (self.next_radius_id + 1) % 256

    def get_req_authenticator(self):
        return os.urandom(16)
