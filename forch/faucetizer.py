"""Collect Faucet information and generate ACLs"""

import argparse
import copy
import logging
import os
import sys
import yaml

from forch.forchestrator import configure_logging
from forch.utils import yaml_proto

from forch.proto.network_state_pb2 import NetworkState

LOGGER = logging.getLogger('faucetizer')


class Device:
    """A device with learning and behavior"""
    def __init__(self):
        self.old_learning = None
        self.new_learning = None
        self.behavior = None

    def has_migrated(self):
        """Determine if the switch or port of a device has changed"""
        if not self.old_learning:
            return False
        is_same_switch = self.old_learning.switch != self.new_learning.switch
        is_same_port = self.old_learning.port != self.new_learning.port
        return not is_same_switch or not is_same_port

    def is_fulfilled(self):
        """Determine if the info of device is enough to update output faucet config"""
        return self.new_learning and self.behavior

    def commit(self):
        self.old_learning = copy.deepcopy(self.new_learning)
        print(f'** old_learning: {self.old_learning}')


class Faucetizer:
    """Collect Faucet information and generate ACLs"""
    def __init__(self, output_file):
        self._devices = {}
        self._base_faucet_config = None
        self._faucet_config = None
        self._output_file = output_file

    def process_network_state(self, network_state):
        """Process network state input"""
        macs = set()
        for mac, learning in network_state.device_mac_learnings.items():
            macs.add(mac)
            self._process_device_learning(mac, learning)
        for mac, behavior in network_state.device_mac_behaviors.items():
            macs.add(mac)
            self._process_device_behavior(mac, behavior)

        self._faucetize(macs)

    def _process_device_learning(self, mac, learning):
        device = self._devices.setdefault(mac, Device())
        device.new_learning = learning

    def _process_device_behavior(self, mac, behavior):
        device = self._devices.setdefault(mac, Device())
        device.behavior = behavior

    def process_faucet_config(self, faucet_config):
        """Process faucet config when base faucet config changes"""
        self._base_faucet_config = faucet_config
        self._faucet_config = faucet_config
        self._faucetize()

    def _faucetize(self, macs=None):
        if not self._faucet_config:
            return

        if not macs:
            macs = self._devices.keys()

        commit = False

        for mac in macs:
            device = self._devices[mac]

            if device.has_migrated():
                self._reset_port_config(device)
                commit = True

            if device.is_fulfilled():
                switch = device.new_learning.switch
                port = device.new_learning.port
                switch_config = self._faucet_config.get('dps', {}).get(switch, {})
                port_config = switch_config.get('interfaces', {}).get(port)
                if not port_config:
                    LOGGER.warning('Switch or port not defined in faucet config: %s %s',
                                   switch, port)
                    continue
                port_config['native_vlan'] = device.behavior.vid
                role = device.behavior.role
                if role:
                    port_config['acls_in'] = [f'role_{role}']
                commit = True

        if commit:
            self._commit_faucet_config(macs)

    def _reset_port_config(self, device):
        switch = device.old_learning.switch
        port = device.old_learning.port
        switch_config = self._faucet_config.get('dps', {}).get(switch, {})
        port_config = switch_config.get('interfaces', {}).get(port)
        if not port_config:
            LOGGER.warning('Switch or port not defined in faucet config: %s %s', switch, port)
            return

        base_switch_config = self._base_faucet_config.get('dps', {}).get(switch, {})
        base_port_config = base_switch_config.get('interfaces', {}).get(port)
        if not base_port_config:
            LOGGER.warning('Switch or port not defined in base faucet config: %s %s', switch, port)
            return

        port_config.update(base_port_config)

    def _commit_faucet_config(self, macs):
        for mac in macs:
            device = self._devices[mac]
            device.commit()

        with open(self._output_file, 'w') as config_output:
            yaml.dump(self._faucet_config, config_output)

        LOGGER.info('Config wrote to %s', self._output_file)


def load_network_state(file):
    """Load network state file"""
    LOGGER.info('Loading network state file %s', file)
    network_state = yaml_proto(file, NetworkState)
    LOGGER.info('Loaded %d devices', len(network_state.device_mac_behaviors))
    return network_state


def load_faucet_config(file):
    """Load network state file"""
    LOGGER.info('Loading faucet config file %s', file)
    with open(file) as config_file:
        faucet_config = yaml.safe_load(config_file)
    LOGGER.info('Loaded base faucet config')
    return faucet_config


def parse_args(raw_args):
    """Parse sys args"""
    parser = argparse.ArgumentParser(prog='faucetizer', description='faucetizer')
    parser.add_argument('-s', '--state-input', type=str, default='network_state.yaml',
                        help='network state input')
    parser.add_argument('-c', '--config-input', type=str, default='faucet.yaml',
                        help='faucet base config input')
    parser.add_argument('-o', '--output', type=str, default='faucet.yaml',
                        help='faucet orchestration config output')
    return parser.parse_args(raw_args)


if __name__ == '__main__':
    configure_logging()
    FORCH_BASE_DIR = os.getenv('FORCH_CONFIG_DIR')
    FAUCET_BASE_DIR = os.getenv('FAUCET_CONFIG_DIR')
    print(sys.argv)
    ARGS = parse_args(sys.argv[1:])

    OUTPUT_FILE = os.path.join(FAUCET_BASE_DIR, ARGS.output)
    FAUCETIZER = Faucetizer(OUTPUT_FILE)

    NETWORK_STATE_FILE = os.path.join(FORCH_BASE_DIR, ARGS.state_input)
    NETWORK_STATE_SAMPLES = load_network_state(NETWORK_STATE_FILE)
    FAUCETIZER.process_network_state(NETWORK_STATE_SAMPLES)

    FAUCET_CONFIG_FILE = os.path.join(FORCH_BASE_DIR, ARGS.config_input)
    FAUCET_CONFIG = load_faucet_config(FAUCET_CONFIG_FILE)
    FAUCETIZER.process_faucet_config(FAUCET_CONFIG)
