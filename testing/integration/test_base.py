"""Integration test base class for Forch"""

import subprocess
import unittest
import os
import sys

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
        command = path + script
        command = ['sudo', command] + arglist
        return self._run_shell_command(command)

    def _setup_stack(self):
        code, out, err = self._run_forch_script('bin/setup_stack', ['local', 'skip-conn-check'])
        logger.debug('setup stack stdout: \n' + str(out, 'utf-8'))
        logger.debug('setup stack stderr: \n' + str(err, 'utf-8'))
        if not code:
            logger.info('setup_stack finished successfully')
        else:
            logger.info('setup_stack failed')

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
        logger.debug('Return code: %s\nstderr: %s' %
                         (return_code, str(err, 'utf-8')))
        return not return_code

    def test_stack(self):
        self._clean_stack()
        self._setup_stack()
        self.assertTrue(self._ping_host('forch-faux-1', '192.168.1.2'))
        self.assertFalse(self._ping_host('forch-faux-1', '192.168.1.12'))
        self._clean_stack()


if __name__ == '__main__':
    unittest.main()
