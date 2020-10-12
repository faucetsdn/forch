"""Integration test base class for Forch"""
import unittest
import time

from integration_base import IntegrationTestBase


class FailScaleConfigTest(IntegrationTestBase):
    """Test suite for failure modes during scaling"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.stack_options.update({
            'devices': 5,
            'switches': 9,
            'mode': 'scale'
        })

    def test_stack_connectivity(self):
        """Test to build stack and check for connectivity"""
        self.assertEqual(10, self._ping_host('forch-faux-8', '192.168.1.0', count=10, output=True),
                         'warm-up ping count')
        process = self._ping_host_process('forch-faux-8', '192.168.1.0', count=40)
        time.sleep(5)
        self._fail_egress_link()
        try:
            ping_count = self._ping_host_reap(process, output=True)
            self.assertTrue(10 < ping_count <= 35, 'disrupted ping count %s' % ping_count)
        except Exception as e:
            self._run_cmd('bin/dump_logs')
            raise e
        self._run_cmd('bin/dump_logs')


if __name__ == '__main__':
    unittest.main()
