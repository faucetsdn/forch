"""Module for proxy server to aggregate and serve data"""

import functools
import threading
import requests

from forch.http_server import HttpServer
from forch.utils import get_logger

LOGGER = get_logger('proxy')
DEFAULT_PROXY_PORT = 8080
LOCALHOST = '0.0.0.0'


class ForchProxy():
    """Class that implements the module that creates a proxy server"""

    def __init__(self, proxy_config):
        self._proxy_config = proxy_config
        self._proxy_port = self._proxy_config.proxy_port or DEFAULT_PROXY_PORT
        self._pages = {}
        self._proxy_server = None

    def start(self):
        """Start proxy server"""
        self._register_pages()
        self._proxy_server = HttpServer(self._proxy_port)
        try:
            self._proxy_server.map_request('', self._get_path_data)
        except Exception as e:
            self._proxy_server.map_request('', functools.partial(self._show_error, e))
        finally:
            threading.Thread(target=self._proxy_server.start_server(), daemon=True).start()
            LOGGER.info('Started proxy server on port %s', self._proxy_port)

    def stop(self):
        """Kill server"""
        LOGGER.info('Stopping proxy server')
        self._proxy_server.stop_server()

    def _get_url(self, server, port):
        return 'http://' + str(server) + ':' + str(port)

    def _register_page(self, path, server, port):
        self._pages[path] = self._get_url(server, port)

    def _register_pages(self):
        for name, target in self._proxy_config.targets.items():
            self._register_page(name, LOCALHOST, target.port)

    def _get_proxy_help(self):
        """Display proxy help"""
        help_str = 'Following paths are supported:\n\n\t'
        for target in self._proxy_config.targets:
            help_str += '/' + target + '\n\t'
        return help_str

    def _get_path_data(self, path, params):
        path = '/'.join(path.split('/')[1:])
        url = self._pages.get(path)
        if not url:
            return self._get_proxy_help()
        try:
            data = requests.get(url)
        except requests.exceptions.RequestException as e:
            return "Error retrieving data from url %s: %s" % (url, str(e))
        return data.content.decode('utf-8')

    def _show_error(self, error, path, params):
        """Display errors"""
        return f"Error creating proxy server: {str(error)}"
