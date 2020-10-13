# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: forch/proto/host_path.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from forch.proto import path_node_pb2 as forch_dot_proto_dot_path__node__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='forch/proto/host_path.proto',
  package='',
  syntax='proto3',
  serialized_options=None,
  serialized_pb=b'\n\x1b\x66orch/proto/host_path.proto\x1a\x1b\x66orch/proto/path_node.proto\"_\n\x08HostPath\x12\x0f\n\x07src_ips\x18\x01 \x03(\t\x12\x0f\n\x07\x64st_ips\x18\x02 \x03(\t\x12\x17\n\x04path\x18\x03 \x03(\x0b\x32\t.PathNode\x12\x18\n\x10system_state_url\x18\x04 \x01(\tb\x06proto3'
  ,
  dependencies=[forch_dot_proto_dot_path__node__pb2.DESCRIPTOR,])




_HOSTPATH = _descriptor.Descriptor(
  name='HostPath',
  full_name='HostPath',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='src_ips', full_name='HostPath.src_ips', index=0,
      number=1, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='dst_ips', full_name='HostPath.dst_ips', index=1,
      number=2, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='path', full_name='HostPath.path', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='system_state_url', full_name='HostPath.system_state_url', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
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
  serialized_start=60,
  serialized_end=155,
)

_HOSTPATH.fields_by_name['path'].message_type = forch_dot_proto_dot_path__node__pb2._PATHNODE
DESCRIPTOR.message_types_by_name['HostPath'] = _HOSTPATH
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

HostPath = _reflection.GeneratedProtocolMessageType('HostPath', (_message.Message,), {
  'DESCRIPTOR' : _HOSTPATH,
  '__module__' : 'forch.proto.host_path_pb2'
  # @@protoc_insertion_point(class_scope:HostPath)
  })
_sym_db.RegisterMessage(HostPath)


# @@protoc_insertion_point(module_scope)
