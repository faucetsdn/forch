"""Scrape varz from Faucet"""
import logging
import time

import prometheus_client.parser
import requests

LOGGER = logging.getLogger('vstate')
_TARGET_METRICS = (
    'port_status',
    'port_lacp_state',
    'dp_status',
    'learned_l2_port',
    'port_stack_state',
    'faucet_config_hash_info',
    'faucet_event_id',
    'dp_root_hop_port',
    'faucet_stack_root_dpid',
    'faucet_config_reload_cold',
    'faucet_config_reload_warm'
)


class VarzStateCollector:
    """Collecting varz"""
    def __init__(self, endpoint, target_metrics=_TARGET_METRICS):
        self._endpoint = endpoint
        self._target_metrics = target_metrics

    def _get_metrics(self):
        metric_map = {}

        response = requests.get(self._endpoint)
        if response.status_code == requests.status_codes.codes.ok:  # pylint: disable=no-member
            content = response.content.decode('utf-8', 'strict')
            metrics = prometheus_client.parser.text_string_to_metric_families(content)
            for metric in [m for m in metrics if m.name in self._target_metrics]:
                metric_map[metric.name] = metric
        else:
            raise Exception(f"Error response code: {response.status_code}")

        return metric_map

    def get_metrics(self, retries=3):
        """Get a list of target metrics"""
        for retry in range(retries):
            try:
                metrics = self._get_metrics()
                if metrics:
                    return metrics
                LOGGER.warning("Metrics are empty, retry: %d", retry)
            except Exception as e:
                LOGGER.warning("Cannot retrieve prometheus metrics: %s, retry: %d", e, retry)
                time.sleep(1)
        raise Exception(f"Cannot retrieve prometheus metrics after {retries} retries")
