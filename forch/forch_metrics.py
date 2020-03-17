"""Module to expose varz interface"""

import functools
import logging

from prometheus_client import Info, generate_latest
import forch.http_server

LOGGER = logging.getLogger('auth')

class ForchMetrics():
    """Class that implements the module that exposes varz for metrics"""
    def __init__(self, local_port, config):
        self._local_port = local_port
        self._config = config
        self._http_server = None
        self._metrics = {}
        self._reg = None

    def start(self):
        """Start serving varz"""
        self._add_vars()
        self._http_server = forch.http_server.HttpServer(self._config, self._local_port)
        try:
            self._http_server.map_request('', self._get_metrics)
        except Exception as e:
            self._http_server.map_request('', functools.partial(self._show_error, e))
        finally:
            self._http_server.start_server()

    def stop(self):
        """Kill varz server"""
        self._http_server.stop_server()

    def update_var(self, var, value):
        """Update given varz with new value"""
        varz = self._metrics.get(var)
        if not varz:
            LOGGER.error('Error updating to varz %s since it is not known.', var)
            return
        if isinstance(varz, Info):
            varz.info(value)
        else:
            LOGGER.error('Error updating to varz %s since it\'s type %s is not known.',
                         var, type(varz))
            return

    def _add_var(self, var, var_help, metric_type):
        """Add varz to be tracked"""
        self._metrics[var] = metric_type(var, var_help, registry=self._reg)

    def _add_vars(self):
        """Initializing list of vars to be tracked"""
        self._add_var('forch_version', 'Current version of forch', Info)

    def _get_metrics(self, path, params):
        generate_latest(self._reg)

    def _show_error(self, error, path, params):
        """Display errors"""
        return f"Error creating varz interface: {str(error)}"
