# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: forch/proto/authentication.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='forch/proto/authentication.proto',
  package='',
  syntax='proto3',
  serialized_pb=_b('\n forch/proto/authentication.proto\">\n\nAuthResult\x12\x11\n\tdevice_id\x18\x01 \x01(\t\x12\x0c\n\x04role\x18\x02 \x01(\t\x12\x0f\n\x07segment\x18\x03 \x01(\tb\x06proto3')
)
_sym_db.RegisterFileDescriptor(DESCRIPTOR)




_AUTHRESULT = _descriptor.Descriptor(
  name='AuthResult',
  full_name='AuthResult',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='device_id', full_name='AuthResult.device_id', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='role', full_name='AuthResult.role', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='segment', full_name='AuthResult.segment', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=36,
  serialized_end=98,
)

DESCRIPTOR.message_types_by_name['AuthResult'] = _AUTHRESULT

AuthResult = _reflection.GeneratedProtocolMessageType('AuthResult', (_message.Message,), dict(
  DESCRIPTOR = _AUTHRESULT,
  __module__ = 'forch.proto.authentication_pb2'
  # @@protoc_insertion_point(class_scope:AuthResult)
  ))
_sym_db.RegisterMessage(AuthResult)


# @@protoc_insertion_point(module_scope)
