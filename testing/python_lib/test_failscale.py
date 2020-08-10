"""Integration test base class for Forch"""
import unittest
import time

from integration_base import IntegrationTestBase, logger


class FailScaleConfigTest(IntegrationTestBase):
    """Test suite for failure modes during scaling"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.STACK_OPTIONS.update({
            'devices': 5,
            'switches': 9,
            'mode': 'scale'
        })

    def test_stack_connectivity(self):
        """Test to build stack and check for connectivity"""
        logger.info('Running test_stack_connectivity %s', str(STACK_OPTIONS))
        self.assertEqual(10, self._ping_host('forch-faux-8', '192.168.1.0', count=10),
                         'warm-up ping count')
        process = self._ping_host_process('forch-faux-8', '192.168.1.0', count=40)
        logger.info('Waiting...')
        time.sleep(5)
        logger.info('Link down')
        self._fail_egress_link()
        ping_count = self._ping_host_reap(process)
        logger.info('Disruption ping count %s' % ping_count)


if __name__ == '__main__':
    unittest.main()
