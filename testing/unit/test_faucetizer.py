"""Unit tests for Faucetizer"""

import os
import unittest

import forch.faucetizer
from forch.faucetizer import Faucetizer

TEST_DATA_DIR = os.getenv('TEST_DATA_DIR')

TEST_METHOD_CONFIGS = {
    'test_faucetize_normal': {
        'forch_config_file': 'forch_dva.yaml',
        'structural_config_file': 'simple_faucet_structural.yaml',
        'behavioral_config_file': 'simple_faucet_behavioral.yaml',
        'segments_to_vlans': 'simple_segments_to_vlans',
    }
}

OUTPUT_BEHAVIROAL_CONFIG_FILE = 'output_faucet_behavioral.yaml'


class TestFaucetizer(unittest.TestCase):
    """Test cases for Faucetizer"""

    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(methodName)
        self._faucetizer = None
        self._output_behavioral_config_file = OUTPUT_BEHAVIROAL_CONFIG_FILE

    def setUp(self):
        print(self._testMethodName) # TODO
        self._configure_faucetizer()

    def tearDown(self):
        self._faucetizer = None
        os.remove(self._output_behavioral_config_file)

    def _configure_faucetizer(self):
        method_config = TEST_METHOD_CONFIGS[self._testMethodName]
        orch_config = forch.faucetizer.load_orch_config(
            os.path.join(TEST_DATA_DIR, method_config['forch_config_file']))
        structural_config_file = os.path.join(
            TEST_DATA_DIR, method_config['structural_config_file'])
        segments_to_vlans = forch.faucetizer.load_segments_to_vlans(
            os.path.join(TEST_DATA_DIR, method_config['segments_to_vlans']))
        behavioral_config_file = self._output_behavioral_config_file
        self._faucetizer = Faucetizer(
            orch_config, structural_config_file, segments_to_vlans.segments_to_vlans,
            behavioral_config_file)

    def test_faucetize_normal(self):
        """Test normal faucetize behavior"""
        print('testing') # TODO
        self._faucetizer.flush_behavioral_config(forch=True)

        method_config = TEST_METHOD_CONFIGS[self._testMethodName]
        expected_behavioral_config = forch.faucetizer.load_faucet_config(
            os.path.join(TEST_DATA_DIR, method_config['behavioral_config_file']))
        output_behavioral_config = forch.faucetizer.load_faucet_config(
            self._output_behavioral_config_file)
        self.assertEqual(output_behavioral_config, expected_behavioral_config) # TODO


if __name__ == '__main__':
    unittest.main()
