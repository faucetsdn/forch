"""Integration test base class for Forch"""
import unittest
import time
import multiprocessing
import yaml

from integration_base import IntegrationTestBase
from build_config import FaucetConfigGenerator

from forch.utils import proto_dict


class FailScaleConfigTest(IntegrationTestBase):
    """Test suite for failure modes during scaling"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.devices = 10
        self.switches = 10
        self.sim_setup_cmd = 'bin/setup_scale'
        self.config_path = '/tmp/scale_config'

        config = proto_dict(
            FaucetConfigGenerator()._create_scale_faucet_config(2, self.switches, self.devices))
        with open(self.config_path, 'w') as config_file:
            yaml.dump(config, config_file)

        self.stack_options.update({
            'devices': self.devices,
            'switches': self.switches,
            'mode': 'scale',
            'overwrite-faucet-config': self.config_path,
            'skip-conn-check': False
        })

    def test_stack_connectivity(self):
        """Test to build stack and check for connectivity"""
        device_list = ['forch-faux-'+str(num) for num in range(1, self.devices * self.switches + 1)]
        ping_counts = {}
        def ping_device(device, ping_count):
            ping_count[0] = self._ping_host(device, '192.168.1.0', count=10, output=True)
            ping_count[1] = self._ping_host(device, '192.168.1.1', count=10, output=True)

        jobs = []
        for device in device_list:
            ping_count = multiprocessing.Array("i", [0, 1])
            ping_counts[device] = ping_count
            process = multiprocessing.Process(target=ping_device, args=[device, ping_count,])
            jobs.append(process)

        for job in jobs:
            job.start()

        for job in jobs:
            job.join()

        for device in ping_counts:
            print('Device %s ping_count: %s' % (device, ping_counts[device][:]))
        for device in ping_counts:
            self.assertLessEqual(1, ping_counts[device][0], 'Device %s \
                                    ping packets to 192.168.1.0 below threshold.' % (device))
            self.assertLessEqual(1, ping_counts[device][1], 'Device %s \
                                    ping packets to 192.168.1.1 below threshold.' % (device))

        self.assertEqual(10, self._ping_host('forch-faux-8', '192.168.1.0', count=10, output=True),
                         'warm-up ping count')

        process = self._ping_host_process('forch-faux-8', '192.168.1.0', count=40)
        time.sleep(5)
        self._fail_egress_link()
        try:
            ping_count = self._ping_host_reap(process, output=True)
            # Check that at least some flow was disrupted, but not too much.
            self.assertTrue(2 < ping_count < 39, 'disrupted ping count %s' % ping_count)
        except Exception as e:
            self._run_cmd('bin/dump_logs')
            raise e
        self._run_cmd('bin/dump_logs')


if __name__ == '__main__':
    unittest.main()
