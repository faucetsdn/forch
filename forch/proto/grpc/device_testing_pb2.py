# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: forch/proto/grpc/device_testing.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from forch.proto import shared_constants_pb2 as forch_dot_proto_dot_shared__constants__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='forch/proto/grpc/device_testing.proto',
  package='',
  syntax='proto3',
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n%forch/proto/grpc/device_testing.proto\x1a\"forch/proto/shared_constants.proto\"M\n\x12\x44\x65viceTestingState\x12\x0b\n\x03mac\x18\x01 \x01(\t\x12*\n\rtesting_state\x18\x02 \x01(\x0e\x32\x13.TestingState.State2D\n\rDeviceTesting\x12\x33\n\x12ReportTestingState\x12\x13.DeviceTestingState\x1a\x06.Empty\"\x00\x62\x06proto3'
  ,
  dependencies=[forch_dot_proto_dot_shared__constants__pb2.DESCRIPTOR,])




_DEVICETESTINGSTATE = _descriptor.Descriptor(
  name='DeviceTestingState',
  full_name='DeviceTestingState',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='mac', full_name='DeviceTestingState.mac', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='testing_state', full_name='DeviceTestingState.testing_state', index=1,
      number=2, type=14, cpp_type=8, label=1,
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
  serialized_start=77,
  serialized_end=154,
)

_DEVICETESTINGSTATE.fields_by_name['testing_state'].enum_type = forch_dot_proto_dot_shared__constants__pb2._TESTINGSTATE_STATE
DESCRIPTOR.message_types_by_name['DeviceTestingState'] = _DEVICETESTINGSTATE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

DeviceTestingState = _reflection.GeneratedProtocolMessageType('DeviceTestingState', (_message.Message,), {
  'DESCRIPTOR' : _DEVICETESTINGSTATE,
  '__module__' : 'forch.proto.grpc.device_testing_pb2'
  # @@protoc_insertion_point(class_scope:DeviceTestingState)
  })
_sym_db.RegisterMessage(DeviceTestingState)



_DEVICETESTING = _descriptor.ServiceDescriptor(
  name='DeviceTesting',
  full_name='DeviceTesting',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_start=156,
  serialized_end=224,
  methods=[
  _descriptor.MethodDescriptor(
    name='ReportTestingState',
    full_name='DeviceTesting.ReportTestingState',
    index=0,
    containing_service=None,
    input_type=_DEVICETESTINGSTATE,
    output_type=forch_dot_proto_dot_shared__constants__pb2._EMPTY,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
])
_sym_db.RegisterServiceDescriptor(_DEVICETESTING)

DESCRIPTOR.services_by_name['DeviceTesting'] = _DEVICETESTING

# @@protoc_insertion_point(module_scope)
