"""Module to expose varz interface"""

import functools
import threading
from prometheus_client import Counter, Gauge, Info, generate_latest, REGISTRY

from forch.http_server import HttpServer
from forch.utils import get_logger

LOGGER = get_logger('metrics')
DEFAULT_VARZ_PORT = 8302


class ForchMetrics():
    """Class that implements the module that exposes varz for metrics"""
    _reg = REGISTRY

    def __init__(self, varz_config):
        self._local_port = varz_config.varz_port or DEFAULT_VARZ_PORT
        LOGGER.info('forch_metrics port is %s', self._local_port)
        self._http_server = None
        self._metrics = {}

    def start(self):
        """Start serving varz"""
        self._add_vars()
        self._http_server = HttpServer(self._local_port)
        try:
            self._http_server.map_request('', self.get_metrics)
        except Exception as e:
            self._http_server.map_request('', functools.partial(self._show_error, e))
        finally:
            threading.Thread(target=self._http_server.start_server(), daemon=True).start()

    def stop(self):
        """Kill varz server"""
        self._http_server.stop_server()

    def _get_varz(self, var, labels=None):
        varz = self._metrics.get(var)
        if labels:
            varz = varz.labels(*labels)
        if not varz:
            LOGGER.error('Error updating to varz %s since it is not known.', var)
            raise RuntimeError('Unknown varz')
        return varz

    def update_var(self, var, value, labels=None):
        """Update given varz with new value"""
        varz = self._get_varz(var, labels)
        if isinstance(varz, Info):
            varz.info(value)
        elif isinstance(varz, Gauge):
            varz.set(value)
        else:
            error_str = 'Error incrementing varz %s since it\'s type %s is not known.' \
                % (var, type(varz))
            raise RuntimeError(error_str)

    def inc_var(self, var, value=1, labels=None):
        """Increment Counter or Gauge variables"""
        varz = self._get_varz(var, labels)
        if isinstance(varz, (Counter, Gauge)):
            varz.inc(value)
        else:
            error_str = 'Error incrementing varz %s since it\'s type %s is not known.' \
                % (var, type(varz))
            raise RuntimeError(error_str)

    def _add_var(self, var, var_help, metric_type, labels=()):
        """Add varz to be tracked"""
        self._metrics[var] = metric_type(var, var_help, labels, registry=self._reg)

    def _add_vars(self):
        """Initializing list of vars to be tracked"""
        self._add_var('forch_version', 'Current version of forch', Info)
        self._add_var('radius_query_timeouts',
                      'No. of RADIUS query timeouts in state machine', Counter)
        self._add_var('radius_query_responses',
                      'No. of RADIUS query responses received from server', Counter)
        self._add_var('process_state', 'Current process state', Gauge, labels=['process'])

        learned_l2_port_help_text = 'learned port of l2 entries'
        learned_l2_port_labels = ['dp_name', 'eth_src', 'vid', 'ip']
        self._add_var('learned_l2_port', learned_l2_port_help_text, Gauge, learned_l2_port_labels)

        self._add_var(
            'dataplane_packet_rate_state_vlan', 'packet rate state of vlan', Gauge, ['vlan'])
        self._add_var(
            'dataplane_packet_count_vlan', 'number of packets in vlan', Gauge, ['vlan'])

        self._add_var(
            'faucet_config_warning_count', 'Count of Faucet configuration warnings', Gauge)
        self._add_var(
            'faucet_config_warning', 'Faucet configuration warning', Gauge, ['key', 'message'])

    def get_metrics(self, path, params):
        """Return metric list in printable form"""
        return generate_latest(self._reg).decode('utf-8')

    def _show_error(self, error, path, params):
        """Display errors"""
        return f"Error creating varz interface: {str(error)}"
