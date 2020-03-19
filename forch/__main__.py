"""Entry point for orchestrator component for controlling a Faucet SDN"""

import argparse
import functools
import logging
import os
import sys

import forch.faucet_event_client
from forch.forchestrator import Forchestrator
import forch.http_server
from forch.proto.forch_configuration_pb2 import ForchConfig
from forch.utils import configure_logging, yaml_proto

from forch.__version__ import __version__

LOGGER = logging.getLogger('forch')

_FORCH_CONFIG_DEFAULT = 'forch.yaml'


def load_config():
    """Load configuration from the configuration file"""
    config_root = os.getenv('FORCH_CONFIG_DIR', '.')
    config_path = os.path.join(config_root, _FORCH_CONFIG_DEFAULT)
    LOGGER.info('Reading config file %s', os.path.abspath(config_path))
    try:
        return yaml_proto(config_path, ForchConfig)
    except Exception as e:
        LOGGER.error('Cannot load config: %s', e)
        return None


def show_error(error, path, params):
    """Display errors"""
    return f"Cannot initialize forch: {str(error)}"


def run_forchestrator():
    """main function to start forch"""
    configure_logging()

    config = load_config()
    if not config:
        LOGGER.error('Invalid config, exiting.')
        sys.exit(1)

    forchestrator = Forchestrator(config)
    http_server = forch.http_server.HttpServer(forchestrator.get_local_port(), config.http)

    try:
        forchestrator.initialize()
        http_server.map_request('system_state', forchestrator.get_system_state)
        http_server.map_request('dataplane_state', forchestrator.get_dataplane_state)
        http_server.map_request('switch_state', forchestrator.get_switch_state)
        http_server.map_request('cpn_state', forchestrator.get_cpn_state)
        http_server.map_request('process_state', forchestrator.get_process_state)
        http_server.map_request('host_path', forchestrator.get_host_path)
        http_server.map_request('list_hosts', forchestrator.get_list_hosts)
        http_server.map_request('sys_config', forchestrator.get_sys_config)
        http_server.map_request('', http_server.static_file(''))
    except Exception as e:
        LOGGER.error("Cannot initialize forch: %s", e, exc_info=True)
        http_server.map_request('', functools.partial(show_error, e))
    finally:
        http_server.start_server()

    if forchestrator.initialized():
        forchestrator.main_loop()
    else:
        try:
            http_server.join_thread()
        except KeyboardInterrupt:
            LOGGER.info('Keyboard interrupt. Exiting.')

    LOGGER.warning('Exiting program')
    http_server.stop_server()
    forchestrator.stop()


def parse_args(raw_args):
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(prog='forch', description='Process some integers.')
    parser.add_argument('-V', '--version', action='store_true', help='print version and exit')
    parsed = parser.parse_args(raw_args)
    return parsed


def main():
    """Main program"""
    args = parse_args(sys.argv[1:])

    if args.version:
        print(f'Forch {__version__}')
        sys.exit()

    run_forchestrator()


if __name__ == '__main__':
    main()
