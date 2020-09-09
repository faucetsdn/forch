"""Talks and listens to RADIUS. Takes a packet object as input"""

import os

from forch.radius import RadiusAttributesList, RadiusAccessRequest, Radius
from forch.radius_attributes import CallingStationId, MessageAuthenticator, \
        NASPort, CalledStationId, ServiceType, NASPortType
from forch.radius_socket import RadiusSocket
from forch.utils import MessageParseError, get_logger

LOGGER = get_logger('rquery')

RADIUS_HEADER_LENGTH = 1 + 1 + 2 + 16

ACCEPT = "ACCEPT"
REJECT = "REJECT"
INVALID_RESP = "INVALID_RESPONSE"

SERVICE_CALL_CHECK = 10
NAS_TYPE_ETHERNET = 15

class RadiusQuery:
    """Maintains socket information and sends out and receives requests form RADIUS server"""
    def __init__(self, socket_info, radius_secret, auth_callback):
        self.next_radius_id = 0
        self._packet_id_to_mac = {}
        self.auth_callback = auth_callback
        self.packet_id_to_req_authenticator = {}
        self.running = True
        # TODO: Find better way to handle secret
        self.radius_secret = radius_secret
        self.radius_socket = RadiusSocket(socket_info.source_ip, socket_info.source_port,
                                          socket_info.server_ip, socket_info.server_port)
        self.radius_socket.setup()

    def get_mac_from_packet_id(self, packet_id):
        """Returns MAC addr for stored packet ID"""
        if packet_id in self._packet_id_to_mac:
            return self._packet_id_to_mac[packet_id]
        LOGGER.warning("Unrecognised packet ID")
        return None

    def receive_radius_messages(self):
        """Listen on socket for incoming messages and decode them"""
        while self.running:
            LOGGER.debug("Waiting for RADIUS messages.")
            packed_message = self.radius_socket.receive()
            try:
                radius = self._decode_radius_response(packed_message)
            except MessageParseError as exception:
                LOGGER.warning("exception: %s. message: %s", packed_message, exception)
                raise
            # TODO: protobuf for received radius message
            code = INVALID_RESP
            if radius.CODE == 2:
                code = ACCEPT
            elif radius.CODE == 3:
                code = REJECT
            src_mac = self.get_mac_from_packet_id(radius.packet_id)['src_mac']
            LOGGER.debug("Received RADIUS msg: Code:%s src:%s attributes:%s",
                         code, src_mac, radius.attributes.to_dict())
            if self.auth_callback:
                attr = radius.attributes.find('Tunnel-Private-Group-ID')
                segment = attr.data().decode('utf-8') if attr else None
                attr = radius.attributes.find('Tunnel-Assignment-ID')
                role = attr.data().decode('utf-8') if attr else None
                self.auth_callback(src_mac, code, segment, role)

    def send_mab_request(self, src_mac, port_id):
        """Encode and send MAB request for MAC address"""
        req_packet = self._encode_mab_message(src_mac, port_id)
        self.radius_socket.send(req_packet)
        LOGGER.info("Sent MAB request for mac %s", src_mac)

    def _encode_mab_message(self, src_mac, port_id=None):
        radius_id = self._get_next_radius_pkt_id()
        req_authenticator = self._get_req_authenticator()
        self._packet_id_to_mac[radius_id] = {'src_mac': src_mac, 'port_id': port_id}
        self.packet_id_to_req_authenticator[radius_id] = req_authenticator

        attr_list = []
        attr_list.append(ServiceType.create(SERVICE_CALL_CHECK))
        attr_list.append(CalledStationId.create(str(src_mac).replace(':', "")))
        attr_list.append(CallingStationId.create(str(src_mac).replace(':', '-')))
        attr_list.append(NASPortType.create(NAS_TYPE_ETHERNET))
        if port_id:
            attr_list.append(NASPort.create(port_id))
        attr_list.append(MessageAuthenticator.create(
            bytes.fromhex("00000000000000000000000000000000")))
        attributes = RadiusAttributesList(attr_list)
        access_request = RadiusAccessRequest(radius_id, req_authenticator, attributes)
        return access_request.build(self.radius_secret)

    def _decode_radius_response(self, packed_msg):
        return Radius.parse(packed_msg, self.radius_secret, self.packet_id_to_req_authenticator)

    def _get_next_radius_pkt_id(self):
        radius_id = self.next_radius_id
        self.next_radius_id = (self.next_radius_id + 1) % 256
        return radius_id

    def _get_req_authenticator(self):
        return os.urandom(16)
