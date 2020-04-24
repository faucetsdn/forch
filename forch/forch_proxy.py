"""Module for proxy server to aggregate and serve data"""

import functools
import logging
import threading
import requests

import forch.http_server

LOGGER = logging.getLogger('proxy')
DEFAULT_PROXY_PORT = 8080
LOCALHOST = '0.0.0.0'


class ForchProxy():
    """Class that implements the module that exposes varz for metrics"""

    def __init__(self, proxy_config):
        self._proxy_config = proxy_config
        self._proxy_port = self._proxy_config.proxy_port or DEFAULT_PROXY_PORT
        self._pages = {}
        self._proxy_server = None

    def start(self):
        """Start serving varz"""
        return
        self._register_pages()
        self._proxy_server = forch.http_server.HttpServer(self._proxy_port)
        try:
            for page in self._pages:
                self._proxy_server.map_request(
                    page, lambda path, params: self._get_path_metrics(path.split('/')[1]))
            self._proxy_server.map_request('', self.get_proxy_help)
        except Exception as e:
            self._proxy_server.map_request('', functools.partial(self._show_error, e))
        finally:
            threading.Thread(target=self._proxy_server.start_server(), daemon=True).start()
            LOGGER.info('Started proxy server on port %s', self._proxy_port)

    def stop(self):
        """Kill varz server"""
        LOGGER.info('Stopping proxy server')
        self._proxy_server.stop_server()

