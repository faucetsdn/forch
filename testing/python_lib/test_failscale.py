"""Integration test base class for Forch"""
import unittest
import time

from integration_base import IntegrationTestBase, logger


class FailScaleConfigTest(IntegrationTestBase):
    """Test suite for failure modes during scaling"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def test_stack_connectivity(self):
        """Test to build stack and check for connectivity"""
        logger.debug('Running test_stack_connectivity')
        self._setup_stack(devices=5, switches=9, mode='scale')
        self.assertEqual(10, self._ping_host('forch-faux-1', '192.168.1.0', count=10),
                         'warm-up ping count')
        process = self._ping_host_process('forch-faux-1', '192.168.1.0', count=40)
        time.sleep(5)
        ping_count = self._ping_host_reap(process)
        logger.info('Disruption ping count %s' % ping_count)
        

if __name__ == '__main__':
    unittest.main()
