# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: forch/proto/vlan_state.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='forch/proto/vlan_state.proto',
  package='',
  syntax='proto3',
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n\x1c\x66orch/proto/vlan_state.proto\"2\n\tVLANState\x12\x0f\n\x07vlan_id\x18\x01 \x01(\x05\x12\x14\n\x0cpacket_count\x18\x02 \x01(\x05\x62\x06proto3'
)




_VLANSTATE = _descriptor.Descriptor(
  name='VLANState',
  full_name='VLANState',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='vlan_id', full_name='VLANState.vlan_id', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='packet_count', full_name='VLANState.packet_count', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=32,
  serialized_end=82,
)

DESCRIPTOR.message_types_by_name['VLANState'] = _VLANSTATE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

VLANState = _reflection.GeneratedProtocolMessageType('VLANState', (_message.Message,), {
  'DESCRIPTOR' : _VLANSTATE,
  '__module__' : 'forch.proto.vlan_state_pb2'
  # @@protoc_insertion_point(class_scope:VLANState)
  })
_sym_db.RegisterMessage(VLANState)


# @@protoc_insertion_point(module_scope)
