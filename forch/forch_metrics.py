"""Module to expose varz interface"""

import functools

import forch.http_server

class ForchMetrics():
    """Class that implements the module that exposes varz for metrics"""
    def __init__(self, local_port, config):
        self._local_port = local_port
        self._config = config
        self._http_server = None
        self._metrics = None

    def start(self):
        """Start serving varz"""
        self._http_server = forch.http_server.HttpServer(self._config, self._local_port)
        try:
            self._http_server.map_request('', self._get_metrics)
        except Exception as e:
            self._http_server.map_request('', functools.partial(self._show_error, e))
        finally:
            self._http_server.start_server()

    def stop(self):
        """Kill server"""
        self._http_server.stop_server()

    def _get_metrics(self, path, params):
        #return self._metrics
        return "Version 1"

    def _show_error(self, error, path, params):
        """Display errors"""
        return f"Error creating varz interface: {str(error)}"
