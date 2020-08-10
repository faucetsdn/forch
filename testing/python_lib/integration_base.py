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

    def _run_shell_command(self, command):
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.wait()
        stdout, stderr = process.communicate()
        return process.returncode, stdout, stderr

    def _run_forch_script(self, script, arglist=[]):
        """Runs scripts from forch base folder"""
        path = os.path.dirname(os.path.abspath(__file__)) + '/../../'
        command = [path + script] + arglist
        return self._run_shell_command(command)

    def _setup_stack(self):
        code, out, err = self._run_forch_script('bin/setup_stack',
                                                ['local', 'skip-conn-check', 'no_clean'])
        time.sleep(15)
        if code:
            logger.info('setup_stack stdout: \n' + str(out, 'utf-8'))
            logger.info('setup_stack stderr: \n' + str(err, 'utf-8'))
            assert False, 'setup_stack failed'

    def _clean_stack(self):
        code, out, err = self._run_forch_script('bin/net_clean')
        logger.debug('clean stack stdout: \n' + str(out, 'utf-8'))
        logger.debug('clean stack stderr: \n' + str(err, 'utf-8'))

    def _ping_host(self, container, host):
        logger.debug('Trying to ping %s from %s' % (host, container))
        ping_cmd = 'docker exec ' + container + ' ping -c 1 ' + host
        cmd_list = ping_cmd.split()
        return_code, out, err = self._run_shell_command(cmd_list)
        logger.debug(str(out, 'utf-8'))
        logger.debug('Return code: %s\nstderr: %s' % (return_code, str(err, 'utf-8')))
        return not return_code

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
