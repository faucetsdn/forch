"""Integration test base class for Forch"""

import subprocess
import unittest
import os
import sys
import time
import yaml

import logging
logger = logging.getLogger()
logger.level = logging.INFO
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)


class IntegrationTestBase(unittest.TestCase):
    """Base class for integration tests"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setUp(self):
        self._clean_stack()

    def tearDown(self):
        self._clean_stack()
        
    def _run_command(self, command):
        return self._reap_process_command(self._run_process_command(command))

    def _run_process_command(self, command):
        command_list = command.split() if isinstance(command, str) else command
        return subprocess.Popen(command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def _reap_process_command(self, process):
        process.wait()
        stdout, stderr = process.communicate()
        return process.returncode, str(stdout, 'utf-8'), str(stderr, 'utf-8')

    def _run_forch_script(self, script, arglist=[]):
        """Runs scripts from forch base folder"""
        path = os.path.dirname(os.path.abspath(__file__)) + '/../../'
        command = [path + script] + arglist
        return self._run_command(command)

    def _setup_stack(self, local=True, devices=None, switches=None, check=False, dhcp=False,
                     clean=False, mode=None):
        stack_args = []
        stack_args.extend(['local'] if local else [])
        stack_args.extend(['devices', str(devices)] if devices else [])
        stack_args.extend(['switches', str(switches)] if devices else [])
        stack_args.extend(['skip-conn-check'] if not check else [])
        stack_args.extend(['dhcp'] if dhcp else [])
        stack_args.extend(['no-clean'] if not clean else [])
        stack_args.extend([mode] if mode else [])

        logger.info('setup_stack ' + ' '.join(stack_args))
        code, out, err = self._run_forch_script('bin/setup_stack', stack_args)
        if code:
            logger.info('setup_stack stdout: \n' + out)
            logger.info('setup_stack stderr: \n' + err)
            assert False, 'setup_stack failed'

        time.sleep(15)

    def _clean_stack(self):
        code, out, err = self._run_forch_script('bin/net_clean')
        logger.debug('clean stack stdout: \n' + out)
        logger.debug('clean stack stderr: \n' + err)

    def _ping_host(self, *args, **kwargs):
        return self._ping_host_reap(self._ping_host_process(*args, **kwargs))

    def _ping_host_process(self, container, host, count=1):
        logger.debug('Trying to ping %s from %s' % (host, container))
        ping_cmd = 'docker exec %s ping -c %d %s' % (container, count, host)
        return self._run_process_command(ping_cmd)

    def _ping_host_reap(self, process, expected=False):
        return_code, out, err = self._reap_process_command(process)
        unexpected = not expected if return_code else expected
        if unexpected:
            logger.warning('ping with %s', str(process.args))
            logger.warning(out)
            logger.warning('Ping return code: %s\nstderr: %s', return_code, err)
        return False if return_code else out.count('icmp_seq')

    def _fail_egress_link(self, alternate=False, restore=False):
        switch = 't1sw2' if alternate else 't1sw1'
        command = 'up' if restore else 'down'
        self._run_command('ip link set %s-eth28 %s' % (switch, command))
        
    def _read_yaml_from_file(self, filename):
        with open(filename) as config_file:
            yaml_object = yaml.load(config_file, yaml.SafeLoader)
        return yaml_object

    def _read_faucet_config(self):
        filename = self._get_faucet_config_path()
        return self._read_yaml_from_file(filename)

    def _write_yaml_to_file(self, filename, yaml_object):
        with open(filename, 'w') as config_file:
            yaml.dump(yaml_object, config_file)

    def _write_faucet_config(self, config):
        filename = self._get_faucet_config_path()
        return self._write_yaml_to_file(filename, config)

    def _get_faucet_config_path(self):
        return os.path.dirname(os.path.abspath(__file__)) + \
            '/../../inst/forch-faucet-1/faucet/faucet.yaml'




if __name__ == '__main__':
    unittest.main()
