"""Scrape varz from Faucet and Gauge"""

import time
import urllib.request

import prometheus_client.parser

from forch.utils import get_logger, MetricsFetchingError


class VarzStateCollector:
    """Collecting metrics from Varzs"""

    def __init__(self):
        self._logger = get_logger('vstate')

    def get_metrics(self, endpoint, target_metrics):
        """Get a list of target metrics"""
        metric_map = {}

        with urllib.request.urlopen(endpoint) as response:
            content = response.read().decode('utf-8', 'strict')
            metrics = prometheus_client.parser.text_string_to_metric_families(content)
            for metric in [m for m in metrics if m.name in target_metrics]:
                metric_map[metric.name] = metric

        return metric_map

    def retry_get_metrics(self, endpoint, target_metrics, retries=3):
        """Get a list of target metrics with configured number of retries"""
        for retry in range(retries):
            try:
                metrics = self.get_metrics(endpoint, target_metrics)
                if metrics:
                    return metrics
                self._logger.warning("Metrics are empty, retry: %d", retry)
            except Exception as e:
                self._logger.debug("Cannot retrieve prometheus metrics: %s, retry: %d", e, retry)
                time.sleep(1)
        raise MetricsFetchingError(f"Cannot retrieve prometheus metrics after {retries} retries")
