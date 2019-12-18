"""Module for managing orchestrator device topologies"""

import logging
import os
import sys

from forch.forchestrator import configure_logging

from forch.utils import yaml_proto

from forch.proto.building_schema_pb2 import BuildingSchema

LOGGER = logging.getLogger('topology')


def load_devices():
    """Load a device specification file"""
    base_dir_name = os.getenv('FORCH_CONFIG_DIR')
    building_schema_file_name = os.path.join(base_dir_name, 'building_schema.yaml')
    LOGGER.info('Loading device spec file %s', building_schema_file_name)
    building_schema = yaml_proto(building_schema_file_name, BuildingSchema)
    loaded_macs = list(building_schema.mac_addrs.keys())
    loaded_macs.sort()
    LOGGER.info('Loaded device spec for devices: %s', loaded_macs)
    sys.stdout.write(str(loaded_macs) + '\n')


if __name__ == '__main__':
    configure_logging()
    load_devices()
