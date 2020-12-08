"""Utility functions for forch"""

import logging
import os
import yaml

from google.protobuf import json_format, text_format

_LOG_FORMAT = '%(asctime)s %(name)-10s %(levelname)-8s %(message)s'
_LOG_DATE_FORMAT = '%b %d %H:%M:%S'
_LOG_LEVEL_DEFAULT = 'INFO'
_LOG_FILE_DEFAULT = '/var/log/faucet/forch.log'


class MessageParseError(Exception):
    """Error for when parsing cannot be successfully completed."""


class ConfigError(Exception):
    """Error for when config isn't valid."""


class FaucetEventOrderError(Exception):
    """Error for when Faucet event is out of sequence"""


class MetricsFetchingError(Exception):
    """Failure of fetching target metrics"""


def get_logger(name):
    """Get a logger"""
    log_file_path = os.getenv('FORCH_LOG', _LOG_FILE_DEFAULT)
    log_handler = logging.FileHandler(log_file_path)

    logging_level = os.getenv('FORCH_LOG_LEVEL', _LOG_LEVEL_DEFAULT)
    log_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _LOG_DATE_FORMAT))
    log_handler.setLevel(logging_level)

    logger = logging.getLogger(name)
    logger.setLevel(logging_level)
    logger.addHandler(log_handler)

    return logger


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


def str_proto(message_text, proto_func):
    """Convert a string represented protobuf message to proto object"""
    return text_format.Parse(message_text, proto_func())
