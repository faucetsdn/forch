"""Module to expose varz interface"""

import functools
import logging
import threading
from prometheus_client import Info, generate_latest, REGISTRY

import forch.http_server

LOGGER = logging.getLogger('metrics')


class ForchMetrics():
    """Class that implements the module that exposes varz for metrics"""
    _reg = REGISTRY

    def __init__(self, local_port):
        self._local_port = local_port
        self._http_server = None
        self._metrics = {}

    def start(self):
        """Start serving varz"""
        self._add_vars()
        self._http_server = forch.http_server.HttpServer(self._local_port)
        try:
            self._http_server.map_request('', self.get_metrics)
        except Exception as e:
            self._http_server.map_request('', functools.partial(self._show_error, e))
        finally:
            threading.Thread(target=self._http_server.start_server(), daemon=True).start()

    def stop(self):
        """Kill varz server"""
        self._http_server.stop_server()

    def update_var(self, var, value):
        """Update given varz with new value"""
        varz = self._metrics.get(var)
        if not varz:
            LOGGER.error('Error updating to varz %s since it is not known.', var)
            raise RuntimeError('Unknown varz')
        if isinstance(varz, Info):
            varz.info(value)
        else:
            LOGGER.error('Error updating to varz %s since it\'s type %s is not known.',
                         var, type(varz))
            raise RuntimeError('Unknown varz type')

    def _add_var(self, var, var_help, metric_type):
        """Add varz to be tracked"""
        self._metrics[var] = metric_type(var, var_help, registry=self._reg)

    def _add_vars(self):
        """Initializing list of vars to be tracked"""
        self._add_var('forch_version', 'Current version of forch', Info)

    def get_metrics(self, path, params):
        """Return metric list in printable form"""
        return generate_latest(self._reg).decode('utf-8')

    def _show_error(self, error, path, params):
        """Display errors"""
        return f"Error creating varz interface: {str(error)}"
