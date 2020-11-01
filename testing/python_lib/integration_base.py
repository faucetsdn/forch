"""Integration test base class for Forch"""

import subprocess
import unittest
import os
import yaml

from tcpdump_helper import TcpdumpHelper


class IntegrationTestBase(unittest.TestCase):
    """Base class for integration tests"""

    TEN_MIN_SEC = 10 * 60

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stack_options = {
            'skip-conn-check': True,
            'no-clean': True
        }
        self.sim_setup_cmd = 'bin/setup_stack'

    def setUp(self):
        self._clean_stack()
        self._setup_stack()

    def tearDown(self):
        self._clean_stack()

    def _run_process_command(self, command, capture=False):
        command_list = command.split() if isinstance(command, str) else command
        pipeout = subprocess.PIPE if capture else None
        return subprocess.Popen(command_list, stdout=pipeout, stderr=pipeout)

    def _reap_process_command(self, process):
        process.wait(timeout=self.TEN_MIN_SEC)
        stdout, stderr = process.communicate()
        strout = str(stdout, 'utf-8') if stdout else None
        strerr = str(stderr, 'utf-8') if stderr else None
        return process.returncode, strout, strerr

    # pylint: disable=too-many-arguments
    def _run_cmd(self, cmd, arglist=None, strict=True,
                 capture=False, docker_container=None):
        command = ("docker exec %s " % docker_container) if docker_container else ""
        command = command.split() + ([cmd] + arglist) if arglist else command + cmd
        retcode, out, err = self._reap_process_command(
            self._run_process_command(command, capture=capture))
        if strict and retcode:
            if capture:
                print('stdout: \n' + out)
                print('stderr: \n' + err)
            raise Exception('Command execution failed: %s' % str(command))
        return retcode, out, err

    @staticmethod
    def tcpdump_helper(*args, **kwargs):
        """Return running TcpdumpHelper instance"""
        return TcpdumpHelper(*args, **kwargs).execute()

    def _setup_stack(self):
        options = self.stack_options
        print("stack_options = %s" % str(options))
        stack_args = []
        stack_args.extend(['local'] if options.get('local') else [])
        devices = options.get('devices')
        stack_args.extend(['devices', str(devices)] if devices else [])
        switches = options.get('switches')
        stack_args.extend(['switches', str(switches)] if switches else [])
        config = options.get('overwrite-faucet-config')
        stack_args.extend(['overwrite-faucet-config', str(config)] if config else [])
        stack_args.extend(['skip-conn-check'] if options.get('skip-conn-check') else [])
        stack_args.extend(['dhcp'] if options.get('dhcp') else [])
        stack_args.extend(['no-clean'] if options.get('no-clean') else [])
        stack_args.extend(['static_switch'] if options.get('static_switch') else [])
        stack_args.extend(['fot'] if options.get('fot') else [])
        mode = options.get('mode')
        stack_args.extend([mode] if mode else [])

        print(self.sim_setup_cmd + ' ' + ' '.join(stack_args))
        self._run_cmd(self.sim_setup_cmd, stack_args)

    def _clean_stack(self):
        self._run_cmd('bin/net_clean')

    def _ping_host(self, container, host, count=1, output=False):
        return self._ping_host_reap(
            self._ping_host_process(container, host, count=count),
            output=output)

    def _ping_host_process(self, container, host, count=1):
        print('ping %s from %s' % (host, container))
        self._run_cmd('date -u')
        ping_cmd = 'docker exec %s ping -c %d %s' % (container, count, host)
        return self._run_process_command(ping_cmd, capture=True)

    def _ping_host_reap(self, process, expected=False, output=False):
        return_code, out, err = self._reap_process_command(process)
        unexpected = not expected if return_code else expected
        if unexpected or output:
            print('ping with %s' % str(process.args))
            print(out)
            print('Ping return code: %d' % return_code)
            print('stderr: %s' % err)
        return False if return_code else out.count('time=')

    def _fail_egress_link(self, alternate=False, restore=False):
        switch = 't1sw2' if alternate else 't1sw1'
        command = 'up' if restore else 'down'
        self._run_cmd('sudo ip link set %s-eth28 %s' % (switch, command))

    def _get_docker_ip(self, container, interface='faux-eth0'):
        _, out, _ = self._run_cmd('ip addr show %s' % (interface),
                                  docker_container=container, capture=True)
        out_list = out.split()
        return out_list[out_list.index('inet') + 1].split('/')[0]

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
        config_file_format = '/../../inst/%s/faucet/faucet.yaml'
        if self.stack_options.get('fot'):
            return os.path.dirname(os.path.abspath(__file__)) + \
                (config_file_format % ('forch-controller-1'))
        return os.path.dirname(os.path.abspath(__file__)) + \
            (config_file_format % ('forch-faucet-1'))


if __name__ == '__main__':
    unittest.main()
