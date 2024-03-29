# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: forch/proto/shared_constants.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
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
  serialized_pb=_b('\n\"forch/proto/shared_constants.proto\"\x8d\x01\n\x05State\"\x83\x01\n\x05State\x12\x0b\n\x07unknown\x10\x00\x12\n\n\x06\x62roken\x10\x01\x12\n\n\x06\x61\x63tive\x10\x02\x12\x0b\n\x07\x64\x61maged\x10\x03\x12\x08\n\x04\x64own\x10\x04\x12\x0b\n\x07healthy\x10\x05\x12\x0c\n\x08inactive\x10\x06\x12\x10\n\x0cinitializing\x10\x07\x12\t\n\x05split\x10\x08\x12\x06\n\x02up\x10\t\"Y\n\tLacpState\"L\n\tLacpState\x12\x0b\n\x07\x64\x65\x66\x61ult\x10\x00\x12\x11\n\x04none\x10\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01\x12\x08\n\x04init\x10\x01\x12\n\n\x06\x61\x63tive\x10\x03\x12\t\n\x05noact\x10\x05\"\x98\x01\n\x08\x44VAState\"\x8b\x01\n\x05State\x12\x0b\n\x07initial\x10\x00\x12\x13\n\x0funauthenticated\x10\x01\x12\x0f\n\x0bsequestered\x10\x02\x12\x16\n\x12static_operational\x10\x03\x12\x17\n\x13\x64ynamic_operational\x10\x04\x12\r\n\tinfracted\x10\x05\x12\x0f\n\x0boperational\x10\x06\"L\n\x08\x41uthMode\"@\n\x04Mode\x12\x0c\n\x08\x64isabled\x10\x00\x12\x0f\n\x0bstatic_only\x10\x01\x12\x10\n\x0c\x64ynamic_only\x10\x02\x12\x07\n\x03\x61ll\x10\x03\"a\n\x08LacpRole\"U\n\x08LacpRole\x12\x0b\n\x07\x64\x65\x66\x61ult\x10\x00\x12\x11\n\x04none\x10\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01\x12\x0e\n\nunselected\x10\x01\x12\x0c\n\x08selected\x10\x02\x12\x0b\n\x07standby\x10\x03\"C\n\x08PortType\"7\n\x04Type\x12\x0b\n\x07unknown\x10\x00\x12\n\n\x06\x61\x63\x63\x65ss\x10\x01\x12\x0b\n\x07testing\x10\x02\x12\t\n\x05other\x10\x03\"W\n\nTestResult\"I\n\nResultCode\x12\x0b\n\x07PENDING\x10\x00\x12\x0b\n\x07STARTED\x10\x01\x12\t\n\x05\x45RROR\x10\x02\x12\n\n\x06PASSED\x10\x03\x12\n\n\x06\x46\x41ILED\x10\x04\"\xf9\x01\n\x0cPortBehavior\"\x8d\x01\n\x08\x42\x65havior\x12\x0b\n\x07unknown\x10\x00\x12\x11\n\rauthenticated\x10\x01\x12\x0b\n\x07\x63leared\x10\x02\x12\x0f\n\x0bsequestered\x10\x03\x12\n\n\x06passed\x10\x04\x12\n\n\x06\x66\x61iled\x10\x05\x12\x13\n\x0f\x64\x65\x61uthenticated\x10\x06\x12\x16\n\x12manual_sequestered\x10\x07\"\x1d\n\tPortState\x12\x08\n\x04\x64own\x10\x00\x12\x06\n\x02up\x10\x01\":\n\x10\x41utoSequestering\x12\x0b\n\x07\x64\x65\x66\x61ult\x10\x00\x12\x0b\n\x07\x65nabled\x10\x01\x12\x0c\n\x08\x64isabled\x10\x02\"\x07\n\x05\x45mptyb\x06proto3')
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
      name='sequestered', index=2, number=2,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='static_operational', index=3, number=3,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='dynamic_operational', index=4, number=4,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='infracted', index=5, number=5,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='operational', index=6, number=6,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=287,
  serialized_end=426,
)
_sym_db.RegisterEnumDescriptor(_DVASTATE_STATE)

_AUTHMODE_MODE = _descriptor.EnumDescriptor(
  name='Mode',
  full_name='AuthMode.Mode',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='disabled', index=0, number=0,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='static_only', index=1, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='dynamic_only', index=2, number=2,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='all', index=3, number=3,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=440,
  serialized_end=504,
)
_sym_db.RegisterEnumDescriptor(_AUTHMODE_MODE)

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
  serialized_start=518,
  serialized_end=603,
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
  serialized_start=617,
  serialized_end=672,
)
_sym_db.RegisterEnumDescriptor(_PORTTYPE_TYPE)

_TESTRESULT_RESULTCODE = _descriptor.EnumDescriptor(
  name='ResultCode',
  full_name='TestResult.ResultCode',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='PENDING', index=0, number=0,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='STARTED', index=1, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ERROR', index=2, number=2,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='PASSED', index=3, number=3,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='FAILED', index=4, number=4,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=688,
  serialized_end=761,
)
_sym_db.RegisterEnumDescriptor(_TESTRESULT_RESULTCODE)

_PORTBEHAVIOR_BEHAVIOR = _descriptor.EnumDescriptor(
  name='Behavior',
  full_name='PortBehavior.Behavior',
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
    _descriptor.EnumValueDescriptor(
      name='deauthenticated', index=6, number=6,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='manual_sequestered', index=7, number=7,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=781,
  serialized_end=922,
)
_sym_db.RegisterEnumDescriptor(_PORTBEHAVIOR_BEHAVIOR)

_PORTBEHAVIOR_PORTSTATE = _descriptor.EnumDescriptor(
  name='PortState',
  full_name='PortBehavior.PortState',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='down', index=0, number=0,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='up', index=1, number=1,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=924,
  serialized_end=953,
)
_sym_db.RegisterEnumDescriptor(_PORTBEHAVIOR_PORTSTATE)

_PORTBEHAVIOR_AUTOSEQUESTERING = _descriptor.EnumDescriptor(
  name='AutoSequestering',
  full_name='PortBehavior.AutoSequestering',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='default', index=0, number=0,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='enabled', index=1, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='disabled', index=2, number=2,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=955,
  serialized_end=1013,
)
_sym_db.RegisterEnumDescriptor(_PORTBEHAVIOR_AUTOSEQUESTERING)


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
  serialized_start=274,
  serialized_end=426,
)


_AUTHMODE = _descriptor.Descriptor(
  name='AuthMode',
  full_name='AuthMode',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _AUTHMODE_MODE,
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=428,
  serialized_end=504,
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
  serialized_start=506,
  serialized_end=603,
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
  serialized_start=605,
  serialized_end=672,
)


_TESTRESULT = _descriptor.Descriptor(
  name='TestResult',
  full_name='TestResult',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _TESTRESULT_RESULTCODE,
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=674,
  serialized_end=761,
)


_PORTBEHAVIOR = _descriptor.Descriptor(
  name='PortBehavior',
  full_name='PortBehavior',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _PORTBEHAVIOR_BEHAVIOR,
    _PORTBEHAVIOR_PORTSTATE,
    _PORTBEHAVIOR_AUTOSEQUESTERING,
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=764,
  serialized_end=1013,
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
  serialized_start=1015,
  serialized_end=1022,
)

_STATE_STATE.containing_type = _STATE
_LACPSTATE_LACPSTATE.containing_type = _LACPSTATE
_DVASTATE_STATE.containing_type = _DVASTATE
_AUTHMODE_MODE.containing_type = _AUTHMODE
_LACPROLE_LACPROLE.containing_type = _LACPROLE
_PORTTYPE_TYPE.containing_type = _PORTTYPE
_TESTRESULT_RESULTCODE.containing_type = _TESTRESULT
_PORTBEHAVIOR_BEHAVIOR.containing_type = _PORTBEHAVIOR
_PORTBEHAVIOR_PORTSTATE.containing_type = _PORTBEHAVIOR
_PORTBEHAVIOR_AUTOSEQUESTERING.containing_type = _PORTBEHAVIOR
DESCRIPTOR.message_types_by_name['State'] = _STATE
DESCRIPTOR.message_types_by_name['LacpState'] = _LACPSTATE
DESCRIPTOR.message_types_by_name['DVAState'] = _DVASTATE
DESCRIPTOR.message_types_by_name['AuthMode'] = _AUTHMODE
DESCRIPTOR.message_types_by_name['LacpRole'] = _LACPROLE
DESCRIPTOR.message_types_by_name['PortType'] = _PORTTYPE
DESCRIPTOR.message_types_by_name['TestResult'] = _TESTRESULT
DESCRIPTOR.message_types_by_name['PortBehavior'] = _PORTBEHAVIOR
DESCRIPTOR.message_types_by_name['Empty'] = _EMPTY
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

State = _reflection.GeneratedProtocolMessageType('State', (_message.Message,), dict(
  DESCRIPTOR = _STATE,
  __module__ = 'forch.proto.shared_constants_pb2'
  # @@protoc_insertion_point(class_scope:State)
  ))
_sym_db.RegisterMessage(State)

LacpState = _reflection.GeneratedProtocolMessageType('LacpState', (_message.Message,), dict(
  DESCRIPTOR = _LACPSTATE,
  __module__ = 'forch.proto.shared_constants_pb2'
  # @@protoc_insertion_point(class_scope:LacpState)
  ))
_sym_db.RegisterMessage(LacpState)

DVAState = _reflection.GeneratedProtocolMessageType('DVAState', (_message.Message,), dict(
  DESCRIPTOR = _DVASTATE,
  __module__ = 'forch.proto.shared_constants_pb2'
  # @@protoc_insertion_point(class_scope:DVAState)
  ))
_sym_db.RegisterMessage(DVAState)

AuthMode = _reflection.GeneratedProtocolMessageType('AuthMode', (_message.Message,), dict(
  DESCRIPTOR = _AUTHMODE,
  __module__ = 'forch.proto.shared_constants_pb2'
  # @@protoc_insertion_point(class_scope:AuthMode)
  ))
_sym_db.RegisterMessage(AuthMode)

LacpRole = _reflection.GeneratedProtocolMessageType('LacpRole', (_message.Message,), dict(
  DESCRIPTOR = _LACPROLE,
  __module__ = 'forch.proto.shared_constants_pb2'
  # @@protoc_insertion_point(class_scope:LacpRole)
  ))
_sym_db.RegisterMessage(LacpRole)

PortType = _reflection.GeneratedProtocolMessageType('PortType', (_message.Message,), dict(
  DESCRIPTOR = _PORTTYPE,
  __module__ = 'forch.proto.shared_constants_pb2'
  # @@protoc_insertion_point(class_scope:PortType)
  ))
_sym_db.RegisterMessage(PortType)

TestResult = _reflection.GeneratedProtocolMessageType('TestResult', (_message.Message,), dict(
  DESCRIPTOR = _TESTRESULT,
  __module__ = 'forch.proto.shared_constants_pb2'
  # @@protoc_insertion_point(class_scope:TestResult)
  ))
_sym_db.RegisterMessage(TestResult)

PortBehavior = _reflection.GeneratedProtocolMessageType('PortBehavior', (_message.Message,), dict(
  DESCRIPTOR = _PORTBEHAVIOR,
  __module__ = 'forch.proto.shared_constants_pb2'
  # @@protoc_insertion_point(class_scope:PortBehavior)
  ))
_sym_db.RegisterMessage(PortBehavior)

Empty = _reflection.GeneratedProtocolMessageType('Empty', (_message.Message,), dict(
  DESCRIPTOR = _EMPTY,
  __module__ = 'forch.proto.shared_constants_pb2'
  # @@protoc_insertion_point(class_scope:Empty)
  ))
_sym_db.RegisterMessage(Empty)


# @@protoc_insertion_point(module_scope)
