"""Integration test base class for Forch"""

import subprocess
import unittest
import os
import sys

from forch.test_lib.integration_base import IntegrationTestBase, logger


class OTConfigTest(IntegrationTestBase):
    """Test suite for dynamic config changes"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def test_stack_connectivity(self):
        """Test to build stack and check for connectivity"""
        logger.debug('Running test_stack_connectivity')
        self._clean_stack()
        self._setup_stack()
        self.assertTrue(self._ping_host('forch-faux-1', '192.168.1.2'))
        self.assertFalse(self._ping_host('forch-faux-1', '192.168.1.12'))
        self._clean_stack()


if __name__ == '__main__':
    unittest.main()
