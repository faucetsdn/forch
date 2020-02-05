"""RADIUS Packets"""
import copy
import hashlib
import hmac
import struct
import logging

import binascii
from forch.radius_attributes import ATTRIBUTE_TYPES, Attribute, MessageAuthenticator
from forch.radius_datatypes import Concat
from forch.utils import MessageParseError

RADIUS_HEADER_LENGTH = 1 + 1 + 2 + 16

PACKET_TYPE_PARSERS = {}

LOGGER = logging.getLogger('radius')


class InvalidResponseAuthenticatorError(Exception):
    """To be used when the ResponseAuthenticator hashes
     (received in packet, and calculated) do not match."""


class InvalidMessageAuthenticatorError(Exception):
    """To be used when the Message-Authenticator hashes
     (received in packet, and calculated) do not match.
    Received packets that throw this error should be 'silently dropped' (logging is fine)."""


class Radius:
    """Radius packet interface which will determin the correct RadiusPacket child class to use"""
    ACCESS_REQUEST = 1
    ACCESS_ACCEPT = 2
    ACCESS_REJECT = 3
    ACCOUNTING_REQUEST = 4
    ACCOUNTING_RESPONSE = 5
    ACCESS_CHALLENGE = 11
    STATUS_SERVER = 12
    STATUS_CLIENT = 13

    @staticmethod
    def parse(packed_message, secret, packet_id_to_request_authenticator=None):
        """
        Args:
            packed_message:
            secret (str): Shared sceret between chewie and RADIUS server.
            packet_id_to_request_authenticator: map to get authenticator for a packet_id
        Returns:
            RadiusPacket - RadiusAccessChallenge/RadiusAccessRequest/
                            RadiusAccessAccept/RadiusAccessFailure
        Raises:
            MessageParseError: if packed_message cannot be parsed
        """
        try:
            code, packet_id, _, authenticator = struct.unpack(
                "!BBH16s", packed_message[:RADIUS_HEADER_LENGTH])
        except struct.error as exception:
            raise MessageParseError('Unable to unpack first 20 bytes of RADIUS header') \
                from exception

        if code in PACKET_TYPE_PARSERS.keys():
            radius_packet = PACKET_TYPE_PARSERS[code](packet_id, authenticator,
                                                      RadiusAttributesList.parse(
                                                          packed_message[RADIUS_HEADER_LENGTH:]))
            if code == Radius.ACCESS_REQUEST:
                request_authenticator = authenticator
            else:
                try:
                    request_authenticator = packet_id_to_request_authenticator[
                        packet_id]
                except KeyError as exception:
                    raise MessageParseError('Unknown RAIDUS packet_id: %s' % packet_id, ) \
                        from exception
            try:
                return radius_packet.validate_packet(secret,
                                                     request_authenticator=request_authenticator,
                                                     code=code)
            except (InvalidMessageAuthenticatorError,
                    InvalidResponseAuthenticatorError) as exception:
                raise MessageParseError("Unable to validate Radius packet") \
                    from exception
        raise MessageParseError("Unable to parse radius code: %d" % code)

    def pack(self):
        """pack"""


def register_packet_type_parser(cls):
    """register packet type parser"""
    PACKET_TYPE_PARSERS[cls.CODE] = cls.parse
    return cls


class RadiusPacket(Radius):
    """super class for different radius packets"""
    CODE = None
    packed = None

    def __init__(self, packet_id, authenticator, attributes):
        self.packet_id = packet_id
        self.authenticator = authenticator
        self.attributes = attributes

    @classmethod
    def parse(cls, packet_id, request_authenticator, attributes): # pylint: disable=arguments-differ
        return cls(packet_id, request_authenticator, attributes)

    def pack(self):
        header = struct.pack("!BBH16s", self.CODE, self.packet_id,
                             RADIUS_HEADER_LENGTH + self.attributes.__len__(),
                             self.authenticator)
        packed_attributes = self.attributes.pack()
        self.packed = bytearray(header + packed_attributes)
        return self.packed

    def build(self, secret=None):
        """Only call this once, or else the MessageAuthenticator will not be zeros,
         resulting in the wrong hash
         Args:
             secret (str): Shared sceret between chewie and RADIUS server.
        Returns:
            packed packet (bytes)"""
        if not self.packed:
            self.pack()
        try:
            position = self.attributes.indexof(MessageAuthenticator.DESCRIPTION) + \
                       RADIUS_HEADER_LENGTH + Attribute.HEADER_SIZE
        except ValueError as err:
            print(err)
            return self.packed

        if secret:
            message_authenticator = bytearray(hmac.new(secret.encode(), self.packed, 'md5')
                                              .digest())

            for index in range(16):
                self.packed[index + position] = message_authenticator[index]
        return self.packed

    def validate_packet(self, secret, request_authenticator=None, code=None):
        """Calculates the Response Authenticator (in Radius Header) and
        MessageAuthenticator (a Radius Attribute) hashes and compares with what was provided.
        Args:
            code (int): The RADIUS Code (e.g. Access-Challenge)
            secret (str): secret shared between RADIUS and chewie.
            request_authenticator (): the original request authenticator for this
             packet (which is a response)
        Raises:
            ValueError: if secret is None or empty string.
            InvalidResponseAuthenticatorError: if Response Authenticator does not match calculated.
            InvalidMessageAuthenticatorError: if MessageAuthenticator does not match calculated.
        """
        # Copy this packet so we can modify the 'Authenticator' and 'Message-Authenticator'
        radius_packet = copy.deepcopy(self)

        if not secret:
            raise ValueError("secret cannot be None for hashing")

        self.validate_response_authenticator(radius_packet, request_authenticator, secret, code)

        self.validate_message_authenticator(radius_packet, secret, request_authenticator)
        return self

    @staticmethod
    def validate_response_authenticator(radius_packet, request_authenticator, secret, code):
        """Validate response authenticator"""
        if request_authenticator and code in [Radius.ACCESS_REJECT,
                                              Radius.ACCESS_ACCEPT,
                                              Radius.ACCESS_CHALLENGE]:
            response_authenticator = radius_packet.authenticator
            radius_packet.authenticator = request_authenticator
            radius_packet.pack()
            calculated_response_authenticator = hashlib.md5(radius_packet.packed +
                                                            bytearray(secret, 'utf-8')).digest()
            if calculated_response_authenticator != response_authenticator:
                raise InvalidResponseAuthenticatorError(
                    "Original ResponseAuthenticator: '%s', does not match calculated: '%s' %s" % (
                        response_authenticator,
                        calculated_response_authenticator,
                        binascii.hexlify(radius_packet.packed)))

    @staticmethod
    def validate_message_authenticator(radius_packet, secret, request_authenticator):
        """Validate message authenticator"""
        message_authenticator = radius_packet.attributes.find(MessageAuthenticator.DESCRIPTION)
        if message_authenticator:

            radius_packet.authenticator = request_authenticator

            original_ma = message_authenticator.bytes_data
            # Replace the Original Message Authenticator
            message_authenticator.bytes_data = bytes.fromhex(
                "00000000000000000000000000000000")

            radius_packet.pack()

            # calculate new hash message authenticator
            new_ma = hmac.new(secret.encode(), radius_packet.packed, 'md5').digest()

            # compare old and new message authenticator
            if original_ma != new_ma:
                raise InvalidMessageAuthenticatorError(
                    "Original Message-Authenticator: '%s', does not match calculated: '%s'" %
                    (binascii.hexlify(original_ma), binascii.hexlify(new_ma)))


@register_packet_type_parser
class RadiusAccessRequest(RadiusPacket):
    """RADIUS Request packet"""
    CODE = Radius.ACCESS_REQUEST


@register_packet_type_parser
class RadiusAccessAccept(RadiusPacket):
    """RADIUS Accept packet"""
    CODE = Radius.ACCESS_ACCEPT


@register_packet_type_parser
class RadiusAccessReject(RadiusPacket):
    """RADIUS Reject packet"""
    CODE = Radius.ACCESS_REJECT


@register_packet_type_parser
class RadiusAccessChallenge(RadiusPacket):
    """RADIUS Challenge packet"""
    CODE = Radius.ACCESS_CHALLENGE


class RadiusAttributesList:
    """Container class for the Radius Attribute Value Pairs"""

    def __init__(self, attributes):
        self.attributes = attributes

    @classmethod
    def parse(cls, attributes_data):
        """

        Args:
            attributes_data:

        Returns:
            RadiusAttributeList
        Raises:
            MessageParseError: if unable to parse an attribute's data.
        """
        attributes = []
        attributes_to_concat = {}
        cls.extract_attributes(attributes_data, attributes, attributes_to_concat)

        attributes = cls.merge_concat_attributes(attributes, attributes_to_concat)

        return cls(attributes)

    @classmethod
    def merge_concat_attributes(cls, attributes, attributes_to_concat):
        """
        Removes concat attributes for attributes list, and inserts a single new master attribute
        for all concat attributes of the same type (e.g. EAPMessage, EAPMessage, = 1 EAPMessage)
        Args:
            attributes (list):
            attributes_to_concat (dict): attribute - position.
        Returns:
            attributes (list)
        Raises:
            MessageParseError: RadiusAttribute.parse will raise error
            if it cannot parse the attribute's data
        """
        # Join Attributes that's datatype is Concat into one attribute.
        concatenated_attributes = []
        for value, list_ in attributes_to_concat.items():
            concatenated_data = b""
            index = 0
            for data, index in list_:
                concatenated_data += data.bytes_data
            concatenated_attributes.append(tuple((ATTRIBUTE_TYPES[value].parse(concatenated_data),
                                                  index)))
        # Remove old Attributes that were concatenated.
        for concat_attr, _ in concatenated_attributes:
            attributes = [x for x in attributes if x.TYPE != concat_attr.TYPE]

        # need to put them back in the same position.
        for concat_attr, index in concatenated_attributes:
            attributes.insert(index, concat_attr)

        return attributes

    @classmethod
    def extract_attributes(cls, attributes_data, attributes, attributes_to_concat):
        """
        Extracts Radius Attributes from a packed payload.
        Keeps track of attribute ordering.
        Args:
            attributes_data (): data to extract from (input).
            attributes: attributes extracted (output variable).
            attributes_to_concat (dict): (output variable).
        Raises:
            MessageParseError: RadiusAttribute.parse will raise error
            if it cannot parse the attribute's data
        """
        total_length = len(attributes_data)
        pos = 0
        index = -1
        last_attribute = -1
        while pos < total_length:
            try:
                type_, attr_length = struct.unpack("!BB",
                                                   attributes_data[pos:pos + Attribute.HEADER_SIZE])
            except struct.error as exception:
                raise MessageParseError('Unable to unpack first 2 bytes of attribute header') \
                    from exception
            data = attributes_data[pos + Attribute.HEADER_SIZE: pos + attr_length]
            pos += attr_length

            packed_value = data[:attr_length - Attribute.HEADER_SIZE]
            try:
                attribute = ATTRIBUTE_TYPES[type_].parse(packed_value)
            except KeyError as exception:
                raise MessageParseError('Cannot find parser for RADIUS attribute %s' %
                                        type_) from exception
            # keep track of where the concated AVP should be in the attributes list.
            # required so the hashing gives correct hash.
            if attribute.DATA_TYPE != Concat or last_attribute != attribute.TYPE:
                index += 1
            last_attribute = attribute.TYPE

            if attribute.DATA_TYPE.DATA_TYPE_VALUE == Concat.DATA_TYPE_VALUE:
                if attribute.TYPE not in attributes_to_concat:
                    attributes_to_concat[attribute.TYPE] = []
                attributes_to_concat[attribute.TYPE].append((attribute, index))

            attributes.append(attribute)

    def find(self, item):
        """Find first attribute that has the matching description
        Args:
            item (str): description of attribute to find
        Returns:
            attribute or None if not found"""
        for attr in self.attributes:
            if item == attr.DESCRIPTION:
                return attr
        return None

    def indexof(self, item):
        """Finds the position (number of bytes) that item is at in list.
        Args:
            item (str): description of attribute to find index of.
        Returns:
            int - number of bytes to item.
        Raises:
            ValueErrpr: if cannot find item
        """
        index = 0
        for attr in self.attributes:
            if item == attr.DESCRIPTION:
                break
            index += attr.full_length()
        else:
            raise ValueError("Cannot find item: %s in attributes list" % item)
        return index

    def __len__(self):
        total = 0
        for attr in self.attributes:
            total = total + attr.full_length()
        return total

    def pack(self):
        """pack and return attributes"""
        packed_attributes = bytes()
        for attr in self.attributes:
            packed_attributes += attr.pack()
        return packed_attributes

    def to_dict(self):
        """Convert object to dict"""
        ret = {}
        for attr in self.attributes:
            ret[attr.DESCRIPTION] = attr.data()
        return ret
