# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: forch/proto/shared_constants.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='forch/proto/shared_constants.proto',
  package='',
  syntax='proto3',
  serialized_options=None,
  serialized_pb=b'\n\"forch/proto/shared_constants.proto\"\x8d\x01\n\x05State\"\x83\x01\n\x05State\x12\x0b\n\x07unknown\x10\x00\x12\n\n\x06\x62roken\x10\x01\x12\n\n\x06\x61\x63tive\x10\x02\x12\x0b\n\x07\x64\x61maged\x10\x03\x12\x08\n\x04\x64own\x10\x04\x12\x0b\n\x07healthy\x10\x05\x12\x0c\n\x08inactive\x10\x06\x12\x10\n\x0cinitializing\x10\x07\x12\t\n\x05split\x10\x08\x12\x06\n\x02up\x10\t\"Y\n\tLacpState\"L\n\tLacpState\x12\x0b\n\x07\x64\x65\x66\x61ult\x10\x00\x12\x11\n\x04none\x10\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01\x12\x08\n\x04init\x10\x01\x12\n\n\x06\x61\x63tive\x10\x03\x12\t\n\x05noact\x10\x05\"c\n\x08\x44VAState\"W\n\x05State\x12\x0b\n\x07initial\x10\x00\x12\x13\n\x0funauthenticated\x10\x01\x12\n\n\x06static\x10\x02\x12\x0f\n\x0bsequestered\x10\x03\x12\x0f\n\x0boperational\x10\x04\"a\n\x08LacpRole\"U\n\x08LacpRole\x12\x0b\n\x07\x64\x65\x66\x61ult\x10\x00\x12\x11\n\x04none\x10\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01\x12\x0e\n\nunselected\x10\x01\x12\x0c\n\x08selected\x10\x02\x12\x0b\n\x07standby\x10\x03\"C\n\x08PortType\"7\n\x04Type\x12\x0b\n\x07unknown\x10\x00\x12\n\n\x06\x61\x63\x63\x65ss\x10\x01\x12\x0b\n\x07testing\x10\x02\x12\t\n\x05other\x10\x03\"l\n\x0b\x44\x65viceEvent\"]\n\x05\x45vent\x12\x0b\n\x07unknown\x10\x00\x12\x11\n\rauthenticated\x10\x01\x12\x0b\n\x07\x63leared\x10\x02\x12\x0f\n\x0bsequestered\x10\x03\x12\n\n\x06passed\x10\x04\x12\n\n\x06\x66\x61iled\x10\x05\"\x07\n\x05\x45mptyb\x06proto3'
)



_STATE_STATE = _descriptor.EnumDescriptor(
  name='State',
  full_name='State.State',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='unknown', index=0, number=0,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='broken', index=1, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='active', index=2, number=2,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='damaged', index=3, number=3,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='down', index=4, number=4,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='healthy', index=5, number=5,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='inactive', index=6, number=6,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='initializing', index=7, number=7,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='split', index=8, number=8,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='up', index=9, number=9,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=49,
  serialized_end=180,
)
_sym_db.RegisterEnumDescriptor(_STATE_STATE)

_LACPSTATE_LACPSTATE = _descriptor.EnumDescriptor(
  name='LacpState',
  full_name='LacpState.LacpState',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='default', index=0, number=0,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='none', index=1, number=-1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='init', index=2, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='active', index=3, number=3,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='noact', index=4, number=5,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=195,
  serialized_end=271,
)
_sym_db.RegisterEnumDescriptor(_LACPSTATE_LACPSTATE)

_DVASTATE_STATE = _descriptor.EnumDescriptor(
  name='State',
  full_name='DVAState.State',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='initial', index=0, number=0,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='unauthenticated', index=1, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='static', index=2, number=2,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='sequestered', index=3, number=3,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='operational', index=4, number=4,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=285,
  serialized_end=372,
)
_sym_db.RegisterEnumDescriptor(_DVASTATE_STATE)

_LACPROLE_LACPROLE = _descriptor.EnumDescriptor(
  name='LacpRole',
  full_name='LacpRole.LacpRole',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='default', index=0, number=0,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='none', index=1, number=-1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='unselected', index=2, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='selected', index=3, number=2,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='standby', index=4, number=3,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=386,
  serialized_end=471,
)
_sym_db.RegisterEnumDescriptor(_LACPROLE_LACPROLE)

_PORTTYPE_TYPE = _descriptor.EnumDescriptor(
  name='Type',
  full_name='PortType.Type',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='unknown', index=0, number=0,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='access', index=1, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='testing', index=2, number=2,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='other', index=3, number=3,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=485,
  serialized_end=540,
)
_sym_db.RegisterEnumDescriptor(_PORTTYPE_TYPE)

_DEVICEEVENT_EVENT = _descriptor.EnumDescriptor(
  name='Event',
  full_name='DeviceEvent.Event',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='unknown', index=0, number=0,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='authenticated', index=1, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='cleared', index=2, number=2,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='sequestered', index=3, number=3,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='passed', index=4, number=4,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='failed', index=5, number=5,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=557,
  serialized_end=650,
)
_sym_db.RegisterEnumDescriptor(_DEVICEEVENT_EVENT)


_STATE = _descriptor.Descriptor(
  name='State',
  full_name='State',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _STATE_STATE,
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=39,
  serialized_end=180,
)


_LACPSTATE = _descriptor.Descriptor(
  name='LacpState',
  full_name='LacpState',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _LACPSTATE_LACPSTATE,
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=182,
  serialized_end=271,
)


_DVASTATE = _descriptor.Descriptor(
  name='DVAState',
  full_name='DVAState',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _DVASTATE_STATE,
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=273,
  serialized_end=372,
)


_LACPROLE = _descriptor.Descriptor(
  name='LacpRole',
  full_name='LacpRole',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _LACPROLE_LACPROLE,
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=374,
  serialized_end=471,
)


_PORTTYPE = _descriptor.Descriptor(
  name='PortType',
  full_name='PortType',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _PORTTYPE_TYPE,
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=473,
  serialized_end=540,
)


_DEVICEEVENT = _descriptor.Descriptor(
  name='DeviceEvent',
  full_name='DeviceEvent',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _DEVICEEVENT_EVENT,
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=542,
  serialized_end=650,
)


_EMPTY = _descriptor.Descriptor(
  name='Empty',
  full_name='Empty',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
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
  serialized_start=652,
  serialized_end=659,
)

_STATE_STATE.containing_type = _STATE
_LACPSTATE_LACPSTATE.containing_type = _LACPSTATE
_DVASTATE_STATE.containing_type = _DVASTATE
_LACPROLE_LACPROLE.containing_type = _LACPROLE
_PORTTYPE_TYPE.containing_type = _PORTTYPE
_DEVICEEVENT_EVENT.containing_type = _DEVICEEVENT
DESCRIPTOR.message_types_by_name['State'] = _STATE
DESCRIPTOR.message_types_by_name['LacpState'] = _LACPSTATE
DESCRIPTOR.message_types_by_name['DVAState'] = _DVASTATE
DESCRIPTOR.message_types_by_name['LacpRole'] = _LACPROLE
DESCRIPTOR.message_types_by_name['PortType'] = _PORTTYPE
DESCRIPTOR.message_types_by_name['DeviceEvent'] = _DEVICEEVENT
DESCRIPTOR.message_types_by_name['Empty'] = _EMPTY
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

State = _reflection.GeneratedProtocolMessageType('State', (_message.Message,), {
  'DESCRIPTOR' : _STATE,
  '__module__' : 'forch.proto.shared_constants_pb2'
  # @@protoc_insertion_point(class_scope:State)
  })
_sym_db.RegisterMessage(State)

LacpState = _reflection.GeneratedProtocolMessageType('LacpState', (_message.Message,), {
  'DESCRIPTOR' : _LACPSTATE,
  '__module__' : 'forch.proto.shared_constants_pb2'
  # @@protoc_insertion_point(class_scope:LacpState)
  })
_sym_db.RegisterMessage(LacpState)

DVAState = _reflection.GeneratedProtocolMessageType('DVAState', (_message.Message,), {
  'DESCRIPTOR' : _DVASTATE,
  '__module__' : 'forch.proto.shared_constants_pb2'
  # @@protoc_insertion_point(class_scope:DVAState)
  })
_sym_db.RegisterMessage(DVAState)

LacpRole = _reflection.GeneratedProtocolMessageType('LacpRole', (_message.Message,), {
  'DESCRIPTOR' : _LACPROLE,
  '__module__' : 'forch.proto.shared_constants_pb2'
  # @@protoc_insertion_point(class_scope:LacpRole)
  })
_sym_db.RegisterMessage(LacpRole)

PortType = _reflection.GeneratedProtocolMessageType('PortType', (_message.Message,), {
  'DESCRIPTOR' : _PORTTYPE,
  '__module__' : 'forch.proto.shared_constants_pb2'
  # @@protoc_insertion_point(class_scope:PortType)
  })
_sym_db.RegisterMessage(PortType)

DeviceEvent = _reflection.GeneratedProtocolMessageType('DeviceEvent', (_message.Message,), {
  'DESCRIPTOR' : _DEVICEEVENT,
  '__module__' : 'forch.proto.shared_constants_pb2'
  # @@protoc_insertion_point(class_scope:DeviceEvent)
  })
_sym_db.RegisterMessage(DeviceEvent)

Empty = _reflection.GeneratedProtocolMessageType('Empty', (_message.Message,), {
  'DESCRIPTOR' : _EMPTY,
  '__module__' : 'forch.proto.shared_constants_pb2'
  # @@protoc_insertion_point(class_scope:Empty)
  })
_sym_db.RegisterMessage(Empty)


# @@protoc_insertion_point(module_scope)
