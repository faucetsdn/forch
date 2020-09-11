"""Scrape varz from Faucet and Gauge"""

import time

import prometheus_client.parser
import requests

from forch.utils import get_logger

LOGGER = get_logger('vstate')


def get_metrics(endpoint, target_metrics):
    """Get a list of target metrics"""
    metric_map = {}

    response = requests.get(endpoint)
    if response.status_code == requests.status_codes.codes.ok:  # pylint: disable=no-member
        content = response.content.decode('utf-8', 'strict')
        metrics = prometheus_client.parser.text_string_to_metric_families(content)
        for metric in [m for m in metrics if m.name in target_metrics]:
            metric_map[metric.name] = metric
    else:
        raise Exception(f"Error response code: {response.status_code}")

    return metric_map


def retry_get_metrics(endpoint, target_metrics, retries=3):
    """Get a list of target metrics with configured number of retries"""
    for retry in range(retries):
        try:
            metrics = get_metrics(endpoint, target_metrics)
            if metrics:
                return metrics
            LOGGER.warning("Metrics are empty, retry: %d", retry)
        except Exception as e:
            LOGGER.warning("Cannot retrieve prometheus metrics: %s, retry: %d", e, retry)
            time.sleep(1)
    raise Exception(f"Cannot retrieve prometheus metrics after {retries} retries")
