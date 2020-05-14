"""Unit tests for Faucetizer"""

import os
import shutil
import tempfile
import unittest
import yaml

from forch.faucetizer import Faucetizer
from forch.proto.forch_configuration_pb2 import OrchestrationConfig
from forch.utils import text_proto

TEST_DATA_DIR = os.getenv('TEST_DATA_DIR')


class FaucetizerTestBase(unittest.TestCase):
    """Base class for Faucetizer unit tests"""

    ORCH_CONFIG = ''
    FAUCET_STRUCTURAL_CONFIG = ''
    FAUCET_BEHAVIORAL_CONFIG = ''
    SEGMENTS_TO_VLANS = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._faucetizer = None
        self._temp_dir = None
        self._temp_structural_config_file = None
        self._temp_behavioral_config_file = None

    def _setup_config_files(self):
        self._temp_dir = tempfile.mkdtemp()
        _, self._temp_structural_config_file = tempfile.mkstemp(dir=self._temp_dir)
        _, self._temp_behavioral_config_file = tempfile.mkstemp(dir=self._temp_dir)

        with open(self._temp_structural_config_file, 'w') as structural_config_file:
            structural_config_file.write(self.FAUCET_STRUCTURAL_CONFIG)

    def _cleanup_config_files(self):
        shutil.rmtree(self._temp_dir)

    def _initialize_faucetizer(self):
        orch_config = text_proto(self.ORCH_CONFIG, OrchestrationConfig)

        self._faucetizer = Faucetizer(
            orch_config, self._temp_structural_config_file, self.SEGMENTS_TO_VLANS, self._temp_behavioral_config_file)
        self._faucetizer.reload_structural_config()


class FaucetizerSimpleTestCase(FaucetizerTestBase):
    """Test basic functionality of Faucetizer"""
    ORCH_CONFIG = 'unauthenticated_vlan: 100'

    FAUCET_STRUCTURAL_CONFIG = """
    dps:
      t2sw1:
        dp_id: 121
        interfaces:
          1:
            description: HOST
            max_hosts: 1
          2:
            description: HOST
            max_hosts: 1
    """

    FAUCET_BEHAVIORAL_CONFIG = """
    dps:
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
    include: []
    """

    def setUp(self):
        self._setup_config_files()
        self._initialize_faucetizer()

    def tearDown(self):
        self._faucetizer = None
        self._cleanup_config_files()

    def test_faucetize_simple(self):
        """Test normal faucetize behavior"""
        self._faucetizer.reload_structural_config()
        self._faucetizer.flush_behavioral_config(force=True)

        expected_behavioral_config = yaml.safe_load(self.FAUCET_BEHAVIORAL_CONFIG)
        with open(self._temp_behavioral_config_file) as temp_behavioral_config_file:
            faucetizer_behavioral_config = yaml.safe_load(temp_behavioral_config_file)

        self.assertEqual(faucetizer_behavioral_config, expected_behavioral_config)


if __name__ == '__main__':
    unittest.main()
