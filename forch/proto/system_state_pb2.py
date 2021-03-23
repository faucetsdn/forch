# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: forch/proto/system_state.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from forch.proto import shared_constants_pb2 as forch_dot_proto_dot_shared__constants__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='forch/proto/system_state.proto',
  package='',
  syntax='proto3',
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n\x1e\x66orch/proto/system_state.proto\x1a\"forch/proto/shared_constants.proto\"\xc3\x07\n\x0bSystemState\x12\x11\n\tsite_name\x18\x01 \x01(\t\x12\'\n\x08versions\x18\x02 \x01(\x0b\x32\x15.SystemState.Versions\x12\x17\n\x0f\x63ontroller_name\x18\x03 \x01(\t\x12\x1b\n\x13peer_controller_url\x18\x04 \x01(\t\x12\"\n\x0csystem_state\x18\x05 \x01(\x0e\x32\x0c.State.State\x12\x1b\n\x13system_state_detail\x18\x06 \x01(\t\x12!\n\x19system_state_change_count\x18\x07 \x01(\x05\x12 \n\x18system_state_last_change\x18\x08 \x01(\t\x12 \n\x18system_state_last_update\x18\t \x01(\t\x12\x31\n\x14\x61uthentication_state\x18\x0c \x01(\x0e\x32\x13.SysAuthState.State\x12\x34\n\x0fsummary_sources\x18\n \x01(\x0b\x32\x1b.SystemState.SummarySources\x12\x32\n\x0e\x63onfig_summary\x18\x0b \x01(\x0b\x32\x1a.SystemState.ConfigSummary\x1a\xeb\x01\n\x0eSummarySources\x12 \n\tcpn_state\x18\x01 \x01(\x0b\x32\r.StateSummary\x12$\n\rprocess_state\x18\x02 \x01(\x0b\x32\r.StateSummary\x12&\n\x0f\x64\x61taplane_state\x18\x03 \x01(\x0b\x32\r.StateSummary\x12#\n\x0cswitch_state\x18\x04 \x01(\x0b\x32\r.StateSummary\x12!\n\nlist_hosts\x18\x05 \x01(\x0b\x32\r.StateSummary\x12!\n\nvrrp_state\x18\x06 \x01(\x0b\x32\r.StateSummary\x1a)\n\x08Versions\x12\x0e\n\x06\x66\x61ucet\x18\x01 \x01(\t\x12\r\n\x05\x66orch\x18\x02 \x01(\t\x1a\xe3\x01\n\rConfigSummary\x12\x36\n\x06hashes\x18\x01 \x03(\x0b\x32&.SystemState.ConfigSummary.HashesEntry\x12:\n\x08warnings\x18\x02 \x03(\x0b\x32(.SystemState.ConfigSummary.WarningsEntry\x1a-\n\x0bHashesEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\x1a/\n\rWarningsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\"\xa9\x01\n\x0cStateSummary\x12\x1b\n\x05state\x18\x01 \x01(\x0e\x32\x0c.State.State\x12\x0e\n\x06\x64\x65tail\x18\x02 \x01(\t\x12\x14\n\x0c\x63hange_count\x18\x03 \x01(\x05\x12\x13\n\x0blast_update\x18\x04 \x01(\t\x12\x13\n\x0blast_change\x18\x05 \x01(\t\x12\x12\n\ndetail_url\x18\x06 \x01(\t\x12\x18\n\x10system_state_url\x18\x07 \x01(\tb\x06proto3'
  ,
  dependencies=[forch_dot_proto_dot_shared__constants__pb2.DESCRIPTOR,])




_SYSTEMSTATE_SUMMARYSOURCES = _descriptor.Descriptor(
  name='SummarySources',
  full_name='SystemState.SummarySources',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='cpn_state', full_name='SystemState.SummarySources.cpn_state', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='process_state', full_name='SystemState.SummarySources.process_state', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='dataplane_state', full_name='SystemState.SummarySources.dataplane_state', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='switch_state', full_name='SystemState.SummarySources.switch_state', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='list_hosts', full_name='SystemState.SummarySources.list_hosts', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='vrrp_state', full_name='SystemState.SummarySources.vrrp_state', index=5,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
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
  serialized_start=526,
  serialized_end=761,
)

_SYSTEMSTATE_VERSIONS = _descriptor.Descriptor(
  name='Versions',
  full_name='SystemState.Versions',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='faucet', full_name='SystemState.Versions.faucet', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='forch', full_name='SystemState.Versions.forch', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
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
  serialized_start=763,
  serialized_end=804,
)

_SYSTEMSTATE_CONFIGSUMMARY_HASHESENTRY = _descriptor.Descriptor(
  name='HashesEntry',
  full_name='SystemState.ConfigSummary.HashesEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='SystemState.ConfigSummary.HashesEntry.key', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='value', full_name='SystemState.ConfigSummary.HashesEntry.value', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=b'8\001',
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=940,
  serialized_end=985,
)

_SYSTEMSTATE_CONFIGSUMMARY_WARNINGSENTRY = _descriptor.Descriptor(
  name='WarningsEntry',
  full_name='SystemState.ConfigSummary.WarningsEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='SystemState.ConfigSummary.WarningsEntry.key', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='value', full_name='SystemState.ConfigSummary.WarningsEntry.value', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=b'8\001',
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=987,
  serialized_end=1034,
)

_SYSTEMSTATE_CONFIGSUMMARY = _descriptor.Descriptor(
  name='ConfigSummary',
  full_name='SystemState.ConfigSummary',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='hashes', full_name='SystemState.ConfigSummary.hashes', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='warnings', full_name='SystemState.ConfigSummary.warnings', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[_SYSTEMSTATE_CONFIGSUMMARY_HASHESENTRY, _SYSTEMSTATE_CONFIGSUMMARY_WARNINGSENTRY, ],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=807,
  serialized_end=1034,
)

_SYSTEMSTATE = _descriptor.Descriptor(
  name='SystemState',
  full_name='SystemState',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='site_name', full_name='SystemState.site_name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='versions', full_name='SystemState.versions', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='controller_name', full_name='SystemState.controller_name', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='peer_controller_url', full_name='SystemState.peer_controller_url', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='system_state', full_name='SystemState.system_state', index=4,
      number=5, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='system_state_detail', full_name='SystemState.system_state_detail', index=5,
      number=6, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='system_state_change_count', full_name='SystemState.system_state_change_count', index=6,
      number=7, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='system_state_last_change', full_name='SystemState.system_state_last_change', index=7,
      number=8, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='system_state_last_update', full_name='SystemState.system_state_last_update', index=8,
      number=9, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='authentication_state', full_name='SystemState.authentication_state', index=9,
      number=12, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='summary_sources', full_name='SystemState.summary_sources', index=10,
      number=10, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='config_summary', full_name='SystemState.config_summary', index=11,
      number=11, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[_SYSTEMSTATE_SUMMARYSOURCES, _SYSTEMSTATE_VERSIONS, _SYSTEMSTATE_CONFIGSUMMARY, ],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=71,
  serialized_end=1034,
)


_STATESUMMARY = _descriptor.Descriptor(
  name='StateSummary',
  full_name='StateSummary',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='state', full_name='StateSummary.state', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='detail', full_name='StateSummary.detail', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='change_count', full_name='StateSummary.change_count', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='last_update', full_name='StateSummary.last_update', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='last_change', full_name='StateSummary.last_change', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='detail_url', full_name='StateSummary.detail_url', index=5,
      number=6, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='system_state_url', full_name='StateSummary.system_state_url', index=6,
      number=7, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
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
  serialized_start=1037,
  serialized_end=1206,
)

_SYSTEMSTATE_SUMMARYSOURCES.fields_by_name['cpn_state'].message_type = _STATESUMMARY
_SYSTEMSTATE_SUMMARYSOURCES.fields_by_name['process_state'].message_type = _STATESUMMARY
_SYSTEMSTATE_SUMMARYSOURCES.fields_by_name['dataplane_state'].message_type = _STATESUMMARY
_SYSTEMSTATE_SUMMARYSOURCES.fields_by_name['switch_state'].message_type = _STATESUMMARY
_SYSTEMSTATE_SUMMARYSOURCES.fields_by_name['list_hosts'].message_type = _STATESUMMARY
_SYSTEMSTATE_SUMMARYSOURCES.fields_by_name['vrrp_state'].message_type = _STATESUMMARY
_SYSTEMSTATE_SUMMARYSOURCES.containing_type = _SYSTEMSTATE
_SYSTEMSTATE_VERSIONS.containing_type = _SYSTEMSTATE
_SYSTEMSTATE_CONFIGSUMMARY_HASHESENTRY.containing_type = _SYSTEMSTATE_CONFIGSUMMARY
_SYSTEMSTATE_CONFIGSUMMARY_WARNINGSENTRY.containing_type = _SYSTEMSTATE_CONFIGSUMMARY
_SYSTEMSTATE_CONFIGSUMMARY.fields_by_name['hashes'].message_type = _SYSTEMSTATE_CONFIGSUMMARY_HASHESENTRY
_SYSTEMSTATE_CONFIGSUMMARY.fields_by_name['warnings'].message_type = _SYSTEMSTATE_CONFIGSUMMARY_WARNINGSENTRY
_SYSTEMSTATE_CONFIGSUMMARY.containing_type = _SYSTEMSTATE
_SYSTEMSTATE.fields_by_name['versions'].message_type = _SYSTEMSTATE_VERSIONS
_SYSTEMSTATE.fields_by_name['system_state'].enum_type = forch_dot_proto_dot_shared__constants__pb2._STATE_STATE
_SYSTEMSTATE.fields_by_name['authentication_state'].enum_type = forch_dot_proto_dot_shared__constants__pb2._SYSAUTHSTATE_STATE
_SYSTEMSTATE.fields_by_name['summary_sources'].message_type = _SYSTEMSTATE_SUMMARYSOURCES
_SYSTEMSTATE.fields_by_name['config_summary'].message_type = _SYSTEMSTATE_CONFIGSUMMARY
_STATESUMMARY.fields_by_name['state'].enum_type = forch_dot_proto_dot_shared__constants__pb2._STATE_STATE
DESCRIPTOR.message_types_by_name['SystemState'] = _SYSTEMSTATE
DESCRIPTOR.message_types_by_name['StateSummary'] = _STATESUMMARY
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

SystemState = _reflection.GeneratedProtocolMessageType('SystemState', (_message.Message,), {

  'SummarySources' : _reflection.GeneratedProtocolMessageType('SummarySources', (_message.Message,), {
    'DESCRIPTOR' : _SYSTEMSTATE_SUMMARYSOURCES,
    '__module__' : 'forch.proto.system_state_pb2'
    # @@protoc_insertion_point(class_scope:SystemState.SummarySources)
    })
  ,

  'Versions' : _reflection.GeneratedProtocolMessageType('Versions', (_message.Message,), {
    'DESCRIPTOR' : _SYSTEMSTATE_VERSIONS,
    '__module__' : 'forch.proto.system_state_pb2'
    # @@protoc_insertion_point(class_scope:SystemState.Versions)
    })
  ,

  'ConfigSummary' : _reflection.GeneratedProtocolMessageType('ConfigSummary', (_message.Message,), {

    'HashesEntry' : _reflection.GeneratedProtocolMessageType('HashesEntry', (_message.Message,), {
      'DESCRIPTOR' : _SYSTEMSTATE_CONFIGSUMMARY_HASHESENTRY,
      '__module__' : 'forch.proto.system_state_pb2'
      # @@protoc_insertion_point(class_scope:SystemState.ConfigSummary.HashesEntry)
      })
    ,

    'WarningsEntry' : _reflection.GeneratedProtocolMessageType('WarningsEntry', (_message.Message,), {
      'DESCRIPTOR' : _SYSTEMSTATE_CONFIGSUMMARY_WARNINGSENTRY,
      '__module__' : 'forch.proto.system_state_pb2'
      # @@protoc_insertion_point(class_scope:SystemState.ConfigSummary.WarningsEntry)
      })
    ,
    'DESCRIPTOR' : _SYSTEMSTATE_CONFIGSUMMARY,
    '__module__' : 'forch.proto.system_state_pb2'
    # @@protoc_insertion_point(class_scope:SystemState.ConfigSummary)
    })
  ,
  'DESCRIPTOR' : _SYSTEMSTATE,
  '__module__' : 'forch.proto.system_state_pb2'
  # @@protoc_insertion_point(class_scope:SystemState)
  })
_sym_db.RegisterMessage(SystemState)
_sym_db.RegisterMessage(SystemState.SummarySources)
_sym_db.RegisterMessage(SystemState.Versions)
_sym_db.RegisterMessage(SystemState.ConfigSummary)
_sym_db.RegisterMessage(SystemState.ConfigSummary.HashesEntry)
_sym_db.RegisterMessage(SystemState.ConfigSummary.WarningsEntry)

StateSummary = _reflection.GeneratedProtocolMessageType('StateSummary', (_message.Message,), {
  'DESCRIPTOR' : _STATESUMMARY,
  '__module__' : 'forch.proto.system_state_pb2'
  # @@protoc_insertion_point(class_scope:StateSummary)
  })
_sym_db.RegisterMessage(StateSummary)


_SYSTEMSTATE_CONFIGSUMMARY_HASHESENTRY._options = None
_SYSTEMSTATE_CONFIGSUMMARY_WARNINGSENTRY._options = None
# @@protoc_insertion_point(module_scope)
