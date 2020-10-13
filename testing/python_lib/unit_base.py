"""Unit test base class for Forch"""

import os
import shutil
import tempfile
import unittest
import yaml

import grpc

from forch.device_testing_server import DeviceTestingServer
from forch.faucetizer import Faucetizer
from forch.faucet_state_collector import FaucetStateCollector
from forch.forchestrator import Forchestrator
from forch.port_state_manager import PortStateManager
from forch.utils import dict_proto

from forch.proto.devices_state_pb2 import DevicePlacement, DeviceBehavior
from forch.proto.forch_configuration_pb2 import ForchConfig
from forch.proto.grpc.device_testing_pb2_grpc import DeviceTestingStub


class UnitTestBase(unittest.TestCase):
    """Base class for unit tests"""

    FORCH_CONFIG = ""
    FAUCET_STRUCTURAL_CONFIG = ""
    FAUCET_BEHAVIORAL_CONFIG = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._temp_dir = None
        self._temp_structural_config_file = None
        self._temp_behavioral_config_file = None
        self._temp_forch_config_file = None
        self._temp_socket_file = None

    def _setup_config_files(self):
        self._temp_dir = tempfile.mkdtemp()
        _, self._temp_structural_config_file = tempfile.mkstemp(dir=self._temp_dir)
        _, self._temp_behavioral_config_file = tempfile.mkstemp(dir=self._temp_dir)
        _, self._temp_forch_config_file = tempfile.mkstemp(dir=self._temp_dir)
        self._temp_socket_file = os.path.join(self._temp_dir, 'faucet_event.sock')

        with open(self._temp_structural_config_file, 'w') as structural_config_file:
            structural_config_file.write(self.FAUCET_STRUCTURAL_CONFIG)

        with open(self._temp_forch_config_file, 'w') as forch_config_file:
            forch_config_file.write(self.FORCH_CONFIG)

    def _cleanup_config_files(self):
        shutil.rmtree(self._temp_dir)


class ForchestratorTestBase(UnitTestBase):
    """Base class for Forchestrator unit tests"""

    FORCH_CONFIG = """
    site:
      name: nz-kiwi
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._forchestrator = None

    def _setup_env(self):
        assert self._temp_dir
        os.environ["FORCH_CONFIG_DIR"] = self._temp_dir
        os.environ["FORCH_CONFIG_FILE"] = os.path.basename(self._temp_forch_config_file)
        os.environ["FAUCET_CONFIG_DIR"] = self._temp_dir
        os.environ["FAUCET_CONFIG_FILE"] = os.path.basename(self._temp_behavioral_config_file)
        os.environ["FAUCET_EVENT_SOCK"] = self._temp_socket_file

    def _initialize_forchestrator(self):
        forch_config = dict_proto(yaml.safe_load(self.FORCH_CONFIG), ForchConfig)
        self._forchestrator = Forchestrator(forch_config)
        self._forchestrator.initialize()

    def setUp(self):
        """setup fixture for each test method"""
        self._setup_config_files()
        self._setup_env()
        self._initialize_forchestrator()

    def tearDown(self):
        """cleanup after each test method finishes"""
        self._cleanup_config_files()


class FaucetizerTestBase(UnitTestBase):
    """Base class for Faucetizer unit tests"""

    FORCH_CONFIG = """
    orchestration:
      unauthenticated_vlan: 100
    """

    FAUCET_STRUCTURAL_CONFIG = """
    dps:
      t1sw1:
        dp_id: 111
        interfaces:
          1:
            output_only: true
          4:
            description: TESTING
            tagged_vlans: [272]
          6:
            stack: {dp: t2sw1, port: 6}
          7:
            stack: {dp: t2sw2, port: 7}
          23:
            lacp: 3
      t2sw1:
        dp_id: 121
        interfaces:
          1:
            description: HOST
            max_hosts: 1
          2:
            description: HOST
            max_hosts: 1
          6:
            stack: {dp: t1sw1, port: 6}
      t2sw2:
        dp_id: 122
        interfaces:
          1:
            description: HOST
            max_hosts: 1
          2:
            description: HOST
            max_hosts: 1
          7:
            stack: {dp: t1sw1, port: 7}
    acls:
      role_red:
        - rule:
            dl_type: 0x800
            actions:
              allow: True
      role_green:
        - rule:
            actions:
              allow: False
      tail_acl:
        - rule:
            actions:
              allow: True
    """

    FAUCET_BEHAVIORAL_CONFIG = """
    dps:
      t1sw1:
        dp_id: 111
        interfaces:
          1:
            output_only: true
          4:
            description: TESTING
            tagged_vlans: [272]
          6:
            stack: {dp: t2sw1, port: 6}
          7:
            stack: {dp: t2sw2, port: 7}
          23:
            lacp: 3
      t2sw1:
        dp_id: 121
        interfaces:
          1:
            description: HOST
            max_hosts: 1
            native_vlan: 100
          2:
            description: HOST
            max_hosts: 1
            native_vlan: 100
          6:
            stack: {dp: t1sw1, port: 6}
      t2sw2:
        dp_id: 122
        interfaces:
          1:
            description: HOST
            max_hosts: 1
            native_vlan: 100
          2:
            description: HOST
            max_hosts: 1
            native_vlan: 100
          7:
            stack: {dp: t1sw1, port: 7}
    acls:
      role_red:
        - rule:
            cookie: 1
            dl_type: 2048
            actions:
              allow: True
      role_green:
        - rule:
            cookie: 2
            actions:
              allow: False
      tail_acl:
        - rule:
            cookie: 3
            actions:
              allow: True
    """

    SEGMENTS_TO_VLANS = """
    segments_to_vlans:
      SEG_A: 200
      SEG_B: 300
      SEG_C: 400
      SEG_X: 1500
      SEG_Y: 1600
      SEG_Z: 1700
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._faucetizer = None
        self._segments_vlans_file = None

    def _setup_config_files(self):
        super()._setup_config_files()

        _, self._segments_vlans_file = tempfile.mkstemp(dir=self._temp_dir)
        with open(self._segments_vlans_file, 'w') as segments_vlans_file:
            segments_vlans_file.write(self.SEGMENTS_TO_VLANS)

    def _initialize_faucetizer(self):
        forch_config = dict_proto(yaml.safe_load(self.FORCH_CONFIG), ForchConfig)

        self._faucetizer = Faucetizer(
            forch_config.orchestration, self._temp_structural_config_file,
            self._temp_behavioral_config_file)
        self._faucetizer.reload_structural_config()
        self._faucetizer.reload_segments_to_vlans(self._segments_vlans_file)

    def _process_device_placement(self, placement_tuple):
        self._faucetizer.process_device_placement(
            placement_tuple[0], dict_proto(placement_tuple[1], DevicePlacement),
            placement_tuple[2])

    def _process_device_behavior(self, behavior_tuple):
        self._faucetizer.process_device_behavior(
            behavior_tuple[0], dict_proto(behavior_tuple[1], DeviceBehavior),
            behavior_tuple[2])

    def _update_port_config(self, behavioral_config, **kwargs):
        port_config = behavioral_config['dps'][kwargs['switch']]['interfaces'][kwargs['port']]
        port_config['native_vlan'] = kwargs.get('native_vlan')
        if 'role' in kwargs:
            port_config['acls_in'] = [f'role_{kwargs["role"]}']
        if 'tail_acl' in kwargs:
            port_config.setdefault('acls_in', []).append(kwargs['tail_acl'])
        if 'tagged_vlans' in kwargs:
            port_config['tagged_vlans'] = kwargs['tagged_vlans']

    def _verify_behavioral_config(self, expected_behavioral_config):
        with open(self._temp_behavioral_config_file) as temp_behavioral_config_file:
            faucetizer_behavioral_config = yaml.safe_load(temp_behavioral_config_file)
        self.assertEqual(faucetizer_behavioral_config, expected_behavioral_config)

    def setUp(self):
        """setup fixture for each test method"""
        self._setup_config_files()
        self._initialize_faucetizer()

    def tearDown(self):
        """cleanup after each test method finishes"""
        self._faucetizer = None
        self._cleanup_config_files()


class DeviceTestingServerTestBase(unittest.TestCase):
    """Base class for device testing server unit test"""
    SERVER_ADDRESS = '0.0.0.0'
    SERVER_PORT = 50051

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._server = None
        self._client = None

    def setUp(self):
        """setup fixture for each test method"""
        channel = grpc.insecure_channel(f'{self.SERVER_ADDRESS}:{self.SERVER_PORT}')
        self._client = DeviceTestingStub(channel)

        self._server = DeviceTestingServer(
            self._process_device_testing_state, self.SERVER_ADDRESS, self.SERVER_PORT)
        self._server.start()

    def _process_device_testing_state(self):
        pass

    def tearDown(self):
        """cleanup after each test method finishes"""
        self._server.stop()


class FaucetStateCollectorTestBase(UnitTestBase):
    """Base class for Faucetizer unit tests"""

    FORCH_CONFIG = """
    event_client:
      stack_topo_change_coalesce_sec: 15
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._faucet_state_collector = None

    def setUp(self):
        """setup fixture for each test method"""
        self._initialize_state_collector()

    def tearDown(self):
        """cleanup after each test method finishes"""
        self._faucet_state_collector = None

    def _initialize_state_collector(self):
        forch_config = dict_proto(yaml.safe_load(self.FORCH_CONFIG), ForchConfig)
        self._faucet_state_collector = FaucetStateCollector(forch_config,
                                                            is_faucetizer_enabled=False)


class PortsStateManagerTestBase(UnitTestBase):
    """Base class for PortsTestingStateManager"""

    AUTHENTICATED = 'authenticated'
    SEQUESTERED = 'sequestered'
    OPERATIONAL = 'operational'
    INFRACTED = 'infracted'
    TESTING_SEGMENT = 'TESTING'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._port_state_manager = PortStateManager(
            self._process_device_behavior, self.TESTING_SEGMENT)
        self._received_device_behaviors = []

    def _process_device_behavior(self):
        pass

    def _verify_ports_states(self, expected_states):
        # pylint: disable=protected-access
        ports_states = {
            mac: ptsm.get_current_state()
            for (mac, ptsm) in self._port_state_manager._state_machines.items()}
        self.assertEqual(ports_states, expected_states)

    def _verify_received_device_behaviors(self, expected_device_behaviors):
        self.assertEqual(self._received_device_behaviors, expected_device_behaviors)
