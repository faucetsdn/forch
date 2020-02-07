"""Utility functions for forch"""

import logging
import os
import yaml

from google.protobuf import json_format

_LOG_FORMAT = '%(asctime)s %(name)-8s %(levelname)-8s %(message)s'
_LOG_DATE_FORMAT = '%b %d %H:%M:%S'


class MessageParseError(Exception):
    """Error for when parsing cannot be successfully completed."""


class ConfigError(Exception):
    """Error for when config isn't valid."""


def get_log_path():
    """Get path for logging"""
    forch_log_dir = os.getenv('FORCH_LOG_DIR')
    if not forch_log_dir:
        return None
    return os.path.join(forch_log_dir, 'forch.log')


def configure_logging():
    """Configure logging with some basic parameters"""
    logging.basicConfig(filename=get_log_path(),
                        format=_LOG_FORMAT,
                        datefmt=_LOG_DATE_FORMAT,
                        level=logging.INFO)


def yaml_proto(file_name, proto_func):
    """Load a yaml file into a proto object"""
    with open(file_name) as stream:
        file_dict = yaml.safe_load(stream)
    return json_format.ParseDict(file_dict, proto_func())


def proto_dict(message,
               including_default_value_fields=False,
               preserving_proto_field_name=True):
    """Convert a proto message to a standard dict object"""
    return json_format.MessageToDict(
        message,
        including_default_value_fields=including_default_value_fields,
        preserving_proto_field_name=preserving_proto_field_name
    )


def proto_json(message):
    """Convert a proto message to a json string"""
    return json_format.MessageToJson(
        message,
        including_default_value_fields=True,
        preserving_proto_field_name=True,
    )


def dict_proto(message, proto_func, ignore_unknown_fields=False):
    """Convert a standard dict object to a proto object"""
    return json_format.ParseDict(message, proto_func(), ignore_unknown_fields)
