# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: forch/proto/dataplane_state.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from forch.proto import shared_constants_pb2 as forch_dot_proto_dot_shared__constants__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='forch/proto/dataplane_state.proto',
  package='',
  syntax='proto3',
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n!forch/proto/dataplane_state.proto\x1a\"forch/proto/shared_constants.proto\"\x97\n\n\x0e\x44\x61taplaneState\x12&\n\x06switch\x18\x01 \x01(\x0b\x32\x16.DataplaneState.Switch\x12$\n\x05stack\x18\x02 \x01(\x0b\x32\x15.DataplaneState.Links\x12&\n\x06\x65gress\x18\x03 \x01(\x0b\x32\x16.DataplaneState.Egress\x12)\n\x05vlans\x18\x04 \x03(\x0b\x32\x1a.DataplaneState.VlansEntry\x12%\n\x0f\x64\x61taplane_state\x18\x05 \x01(\x0e\x32\x0c.State.State\x12\x1e\n\x16\x64\x61taplane_state_detail\x18\x06 \x01(\t\x12$\n\x1c\x64\x61taplane_state_change_count\x18\x07 \x01(\x05\x12#\n\x1b\x64\x61taplane_state_last_change\x18\x08 \x01(\t\x12\x18\n\x10system_state_url\x18\t \x01(\t\x1aG\n\nVlansEntry\x12\x0b\n\x03key\x18\x01 \x01(\x05\x12(\n\x05value\x18\x02 \x01(\x0b\x32\x19.DataplaneState.VLANState:\x02\x38\x01\x1a\xd4\x01\n\x06Switch\x12\x36\n\x08switches\x18\x01 \x03(\x0b\x32$.DataplaneState.Switch.SwitchesEntry\x12!\n\x19switch_state_change_count\x18\x02 \x01(\x05\x12 \n\x18switch_state_last_change\x18\x03 \x01(\t\x1aM\n\rSwitchesEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12+\n\x05value\x18\x02 \x01(\x0b\x32\x1c.DataplaneState.SwitchStatus:\x02\x38\x01\x1a\xb9\x01\n\x05Links\x12/\n\x05links\x18\x01 \x03(\x0b\x32 .DataplaneState.Links.LinksEntry\x12\x1a\n\x12links_change_count\x18\x02 \x01(\x05\x12\x19\n\x11links_last_change\x18\x03 \x01(\t\x1aH\n\nLinksEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12)\n\x05value\x18\x02 \x01(\x0b\x32\x1a.DataplaneState.LinkStatus:\x02\x38\x01\x1a\xc1\x02\n\x06\x45gress\x12\"\n\x0c\x65gress_state\x18\x01 \x01(\x0e\x32\x0c.State.State\x12\x1b\n\x13\x65gress_state_detail\x18\x02 \x01(\t\x12!\n\x19\x65gress_state_change_count\x18\x03 \x01(\x05\x12 \n\x18\x65gress_state_last_change\x18\x04 \x01(\t\x12 \n\x18\x65gress_state_last_update\x18\x05 \x01(\t\x12\x13\n\x0b\x61\x63tive_root\x18\x06 \x01(\t\x12\x30\n\x05links\x18\x07 \x03(\x0b\x32!.DataplaneState.Egress.LinksEntry\x1aH\n\nLinksEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12)\n\x05value\x18\x02 \x01(\x0b\x32\x1a.DataplaneState.LinkStatus:\x02\x38\x01\x1a\x32\n\x0cSwitchStatus\x12\"\n\x0cswitch_state\x18\x01 \x01(\x0e\x32\x0c.State.State\x1a.\n\nLinkStatus\x12 \n\nlink_state\x18\x01 \x01(\x0e\x32\x0c.State.State\x1a\x34\n\tVLANState\x12\'\n\x11packet_rate_state\x18\x01 \x01(\x0e\x32\x0c.State.Stateb\x06proto3'
  ,
  dependencies=[forch_dot_proto_dot_shared__constants__pb2.DESCRIPTOR,])




_DATAPLANESTATE_VLANSENTRY = _descriptor.Descriptor(
  name='VlansEntry',
  full_name='DataplaneState.VlansEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='DataplaneState.VlansEntry.key', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='value', full_name='DataplaneState.VlansEntry.value', index=1,
      number=2, type=11, cpp_type=10, label=1,
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
  serialized_options=b'8\001',
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=425,
  serialized_end=496,
)

_DATAPLANESTATE_SWITCH_SWITCHESENTRY = _descriptor.Descriptor(
  name='SwitchesEntry',
  full_name='DataplaneState.Switch.SwitchesEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='DataplaneState.Switch.SwitchesEntry.key', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='value', full_name='DataplaneState.Switch.SwitchesEntry.value', index=1,
      number=2, type=11, cpp_type=10, label=1,
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
  serialized_options=b'8\001',
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=634,
  serialized_end=711,
)

_DATAPLANESTATE_SWITCH = _descriptor.Descriptor(
  name='Switch',
  full_name='DataplaneState.Switch',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='switches', full_name='DataplaneState.Switch.switches', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='switch_state_change_count', full_name='DataplaneState.Switch.switch_state_change_count', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='switch_state_last_change', full_name='DataplaneState.Switch.switch_state_last_change', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[_DATAPLANESTATE_SWITCH_SWITCHESENTRY, ],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=499,
  serialized_end=711,
)

_DATAPLANESTATE_LINKS_LINKSENTRY = _descriptor.Descriptor(
  name='LinksEntry',
  full_name='DataplaneState.Links.LinksEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='DataplaneState.Links.LinksEntry.key', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='value', full_name='DataplaneState.Links.LinksEntry.value', index=1,
      number=2, type=11, cpp_type=10, label=1,
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
  serialized_options=b'8\001',
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=827,
  serialized_end=899,
)

_DATAPLANESTATE_LINKS = _descriptor.Descriptor(
  name='Links',
  full_name='DataplaneState.Links',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='links', full_name='DataplaneState.Links.links', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='links_change_count', full_name='DataplaneState.Links.links_change_count', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='links_last_change', full_name='DataplaneState.Links.links_last_change', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[_DATAPLANESTATE_LINKS_LINKSENTRY, ],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=714,
  serialized_end=899,
)

_DATAPLANESTATE_EGRESS_LINKSENTRY = _descriptor.Descriptor(
  name='LinksEntry',
  full_name='DataplaneState.Egress.LinksEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='DataplaneState.Egress.LinksEntry.key', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='value', full_name='DataplaneState.Egress.LinksEntry.value', index=1,
      number=2, type=11, cpp_type=10, label=1,
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
  serialized_options=b'8\001',
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=827,
  serialized_end=899,
)

_DATAPLANESTATE_EGRESS = _descriptor.Descriptor(
  name='Egress',
  full_name='DataplaneState.Egress',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='egress_state', full_name='DataplaneState.Egress.egress_state', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='egress_state_detail', full_name='DataplaneState.Egress.egress_state_detail', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='egress_state_change_count', full_name='DataplaneState.Egress.egress_state_change_count', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='egress_state_last_change', full_name='DataplaneState.Egress.egress_state_last_change', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='egress_state_last_update', full_name='DataplaneState.Egress.egress_state_last_update', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='active_root', full_name='DataplaneState.Egress.active_root', index=5,
      number=6, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='links', full_name='DataplaneState.Egress.links', index=6,
      number=7, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[_DATAPLANESTATE_EGRESS_LINKSENTRY, ],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=902,
  serialized_end=1223,
)

_DATAPLANESTATE_SWITCHSTATUS = _descriptor.Descriptor(
  name='SwitchStatus',
  full_name='DataplaneState.SwitchStatus',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='switch_state', full_name='DataplaneState.SwitchStatus.switch_state', index=0,
      number=1, type=14, cpp_type=8, label=1,
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
  serialized_start=1225,
  serialized_end=1275,
)

_DATAPLANESTATE_LINKSTATUS = _descriptor.Descriptor(
  name='LinkStatus',
  full_name='DataplaneState.LinkStatus',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='link_state', full_name='DataplaneState.LinkStatus.link_state', index=0,
      number=1, type=14, cpp_type=8, label=1,
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
  serialized_start=1277,
  serialized_end=1323,
)

_DATAPLANESTATE_VLANSTATE = _descriptor.Descriptor(
  name='VLANState',
  full_name='DataplaneState.VLANState',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='packet_rate_state', full_name='DataplaneState.VLANState.packet_rate_state', index=0,
      number=1, type=14, cpp_type=8, label=1,
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
  serialized_start=1325,
  serialized_end=1377,
)

_DATAPLANESTATE = _descriptor.Descriptor(
  name='DataplaneState',
  full_name='DataplaneState',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='switch', full_name='DataplaneState.switch', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='stack', full_name='DataplaneState.stack', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='egress', full_name='DataplaneState.egress', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='vlans', full_name='DataplaneState.vlans', index=3,
      number=4, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='dataplane_state', full_name='DataplaneState.dataplane_state', index=4,
      number=5, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='dataplane_state_detail', full_name='DataplaneState.dataplane_state_detail', index=5,
      number=6, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='dataplane_state_change_count', full_name='DataplaneState.dataplane_state_change_count', index=6,
      number=7, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='dataplane_state_last_change', full_name='DataplaneState.dataplane_state_last_change', index=7,
      number=8, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='system_state_url', full_name='DataplaneState.system_state_url', index=8,
      number=9, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[_DATAPLANESTATE_VLANSENTRY, _DATAPLANESTATE_SWITCH, _DATAPLANESTATE_LINKS, _DATAPLANESTATE_EGRESS, _DATAPLANESTATE_SWITCHSTATUS, _DATAPLANESTATE_LINKSTATUS, _DATAPLANESTATE_VLANSTATE, ],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=74,
  serialized_end=1377,
)

_DATAPLANESTATE_VLANSENTRY.fields_by_name['value'].message_type = _DATAPLANESTATE_VLANSTATE
_DATAPLANESTATE_VLANSENTRY.containing_type = _DATAPLANESTATE
_DATAPLANESTATE_SWITCH_SWITCHESENTRY.fields_by_name['value'].message_type = _DATAPLANESTATE_SWITCHSTATUS
_DATAPLANESTATE_SWITCH_SWITCHESENTRY.containing_type = _DATAPLANESTATE_SWITCH
_DATAPLANESTATE_SWITCH.fields_by_name['switches'].message_type = _DATAPLANESTATE_SWITCH_SWITCHESENTRY
_DATAPLANESTATE_SWITCH.containing_type = _DATAPLANESTATE
_DATAPLANESTATE_LINKS_LINKSENTRY.fields_by_name['value'].message_type = _DATAPLANESTATE_LINKSTATUS
_DATAPLANESTATE_LINKS_LINKSENTRY.containing_type = _DATAPLANESTATE_LINKS
_DATAPLANESTATE_LINKS.fields_by_name['links'].message_type = _DATAPLANESTATE_LINKS_LINKSENTRY
_DATAPLANESTATE_LINKS.containing_type = _DATAPLANESTATE
_DATAPLANESTATE_EGRESS_LINKSENTRY.fields_by_name['value'].message_type = _DATAPLANESTATE_LINKSTATUS
_DATAPLANESTATE_EGRESS_LINKSENTRY.containing_type = _DATAPLANESTATE_EGRESS
_DATAPLANESTATE_EGRESS.fields_by_name['egress_state'].enum_type = forch_dot_proto_dot_shared__constants__pb2._STATE_STATE
_DATAPLANESTATE_EGRESS.fields_by_name['links'].message_type = _DATAPLANESTATE_EGRESS_LINKSENTRY
_DATAPLANESTATE_EGRESS.containing_type = _DATAPLANESTATE
_DATAPLANESTATE_SWITCHSTATUS.fields_by_name['switch_state'].enum_type = forch_dot_proto_dot_shared__constants__pb2._STATE_STATE
_DATAPLANESTATE_SWITCHSTATUS.containing_type = _DATAPLANESTATE
_DATAPLANESTATE_LINKSTATUS.fields_by_name['link_state'].enum_type = forch_dot_proto_dot_shared__constants__pb2._STATE_STATE
_DATAPLANESTATE_LINKSTATUS.containing_type = _DATAPLANESTATE
_DATAPLANESTATE_VLANSTATE.fields_by_name['packet_rate_state'].enum_type = forch_dot_proto_dot_shared__constants__pb2._STATE_STATE
_DATAPLANESTATE_VLANSTATE.containing_type = _DATAPLANESTATE
_DATAPLANESTATE.fields_by_name['switch'].message_type = _DATAPLANESTATE_SWITCH
_DATAPLANESTATE.fields_by_name['stack'].message_type = _DATAPLANESTATE_LINKS
_DATAPLANESTATE.fields_by_name['egress'].message_type = _DATAPLANESTATE_EGRESS
_DATAPLANESTATE.fields_by_name['vlans'].message_type = _DATAPLANESTATE_VLANSENTRY
_DATAPLANESTATE.fields_by_name['dataplane_state'].enum_type = forch_dot_proto_dot_shared__constants__pb2._STATE_STATE
DESCRIPTOR.message_types_by_name['DataplaneState'] = _DATAPLANESTATE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

DataplaneState = _reflection.GeneratedProtocolMessageType('DataplaneState', (_message.Message,), {

  'VlansEntry' : _reflection.GeneratedProtocolMessageType('VlansEntry', (_message.Message,), {
    'DESCRIPTOR' : _DATAPLANESTATE_VLANSENTRY,
    '__module__' : 'forch.proto.dataplane_state_pb2'
    # @@protoc_insertion_point(class_scope:DataplaneState.VlansEntry)
    })
  ,

  'Switch' : _reflection.GeneratedProtocolMessageType('Switch', (_message.Message,), {

    'SwitchesEntry' : _reflection.GeneratedProtocolMessageType('SwitchesEntry', (_message.Message,), {
      'DESCRIPTOR' : _DATAPLANESTATE_SWITCH_SWITCHESENTRY,
      '__module__' : 'forch.proto.dataplane_state_pb2'
      # @@protoc_insertion_point(class_scope:DataplaneState.Switch.SwitchesEntry)
      })
    ,
    'DESCRIPTOR' : _DATAPLANESTATE_SWITCH,
    '__module__' : 'forch.proto.dataplane_state_pb2'
    # @@protoc_insertion_point(class_scope:DataplaneState.Switch)
    })
  ,

  'Links' : _reflection.GeneratedProtocolMessageType('Links', (_message.Message,), {

    'LinksEntry' : _reflection.GeneratedProtocolMessageType('LinksEntry', (_message.Message,), {
      'DESCRIPTOR' : _DATAPLANESTATE_LINKS_LINKSENTRY,
      '__module__' : 'forch.proto.dataplane_state_pb2'
      # @@protoc_insertion_point(class_scope:DataplaneState.Links.LinksEntry)
      })
    ,
    'DESCRIPTOR' : _DATAPLANESTATE_LINKS,
    '__module__' : 'forch.proto.dataplane_state_pb2'
    # @@protoc_insertion_point(class_scope:DataplaneState.Links)
    })
  ,

  'Egress' : _reflection.GeneratedProtocolMessageType('Egress', (_message.Message,), {

    'LinksEntry' : _reflection.GeneratedProtocolMessageType('LinksEntry', (_message.Message,), {
      'DESCRIPTOR' : _DATAPLANESTATE_EGRESS_LINKSENTRY,
      '__module__' : 'forch.proto.dataplane_state_pb2'
      # @@protoc_insertion_point(class_scope:DataplaneState.Egress.LinksEntry)
      })
    ,
    'DESCRIPTOR' : _DATAPLANESTATE_EGRESS,
    '__module__' : 'forch.proto.dataplane_state_pb2'
    # @@protoc_insertion_point(class_scope:DataplaneState.Egress)
    })
  ,

  'SwitchStatus' : _reflection.GeneratedProtocolMessageType('SwitchStatus', (_message.Message,), {
    'DESCRIPTOR' : _DATAPLANESTATE_SWITCHSTATUS,
    '__module__' : 'forch.proto.dataplane_state_pb2'
    # @@protoc_insertion_point(class_scope:DataplaneState.SwitchStatus)
    })
  ,

  'LinkStatus' : _reflection.GeneratedProtocolMessageType('LinkStatus', (_message.Message,), {
    'DESCRIPTOR' : _DATAPLANESTATE_LINKSTATUS,
    '__module__' : 'forch.proto.dataplane_state_pb2'
    # @@protoc_insertion_point(class_scope:DataplaneState.LinkStatus)
    })
  ,

  'VLANState' : _reflection.GeneratedProtocolMessageType('VLANState', (_message.Message,), {
    'DESCRIPTOR' : _DATAPLANESTATE_VLANSTATE,
    '__module__' : 'forch.proto.dataplane_state_pb2'
    # @@protoc_insertion_point(class_scope:DataplaneState.VLANState)
    })
  ,
  'DESCRIPTOR' : _DATAPLANESTATE,
  '__module__' : 'forch.proto.dataplane_state_pb2'
  # @@protoc_insertion_point(class_scope:DataplaneState)
  })
_sym_db.RegisterMessage(DataplaneState)
_sym_db.RegisterMessage(DataplaneState.VlansEntry)
_sym_db.RegisterMessage(DataplaneState.Switch)
_sym_db.RegisterMessage(DataplaneState.Switch.SwitchesEntry)
_sym_db.RegisterMessage(DataplaneState.Links)
_sym_db.RegisterMessage(DataplaneState.Links.LinksEntry)
_sym_db.RegisterMessage(DataplaneState.Egress)
_sym_db.RegisterMessage(DataplaneState.Egress.LinksEntry)
_sym_db.RegisterMessage(DataplaneState.SwitchStatus)
_sym_db.RegisterMessage(DataplaneState.LinkStatus)
_sym_db.RegisterMessage(DataplaneState.VLANState)


_DATAPLANESTATE_VLANSENTRY._options = None
_DATAPLANESTATE_SWITCH_SWITCHESENTRY._options = None
_DATAPLANESTATE_LINKS_LINKSENTRY._options = None
_DATAPLANESTATE_EGRESS_LINKSENTRY._options = None
# @@protoc_insertion_point(module_scope)
