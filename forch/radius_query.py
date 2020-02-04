"""Talks and listens to RADIUS. Takes a packet object as input"""
from queue import Queue
import logging
import os
from time import sleep
import json

from forch.radius import RadiusAttributesList, RadiusAccessRequest, Radius
from forch.radius_attributes import CallingStationId, UserName, MessageAuthenticator, \
        NASPort, UserPassword
from forch.radius_socket import RadiusSocket
from forch.utils import MessageParseError

LOGGER = logging.getLogger('rquery')

RADIUS_HEADER_LENGTH = 1 + 1 + 2 + 16

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
            LOGGER.info("Received RADIUS msg: Code:%s packet_id:%s attributes:%s", radius.CODE, radius.packet_id, radius.attributes.to_dict())

    def send_mab_request(self, src_mac, port_id):
        req_packet = self.encode_mab_message(src_mac, port_id)
        LOGGER.info("Sending MAB request for mac %s", src_mac)
        self.radius_socket.send(req_packet)

    def encode_mab_message(self, src_mac, port_id=None):
        radius_id = self.get_next_radius_pkt_id()
        req_authenticator = self.get_req_authenticator()
        self.packet_id_to_mac[radius_id] = {'src_mac': src_mac, 'port_id': port_id}
        self.packet_id_to_req_authenticator[radius_id] = req_authenticator

        attr_list = []
        mac_str = str(src_mac).replace(':', "")
        attr_list.append(UserName.create(mac_str))
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
        return access_request.build(self.radius_secret)

    def decode_radius_response(self, packed_msg):
        return Radius.parse(packed_msg, self.radius_secret, self.packet_id_to_req_authenticator)

    def get_next_radius_pkt_id(self):
        radius_id = self.next_radius_id
        self.next_radius_id = (self.next_radius_id + 1) % 256
        return radius_id

    def get_req_authenticator(self):
        return os.urandom(16)
