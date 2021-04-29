"""Module for proxy server to aggregate and serve data"""

import functools
import threading
import urllib.request

from forch.http_server import HttpServer
from forch.utils import get_logger

DEFAULT_PROXY_PORT = 8080
DEFAULT_SERVER_ADDRESS = '127.0.0.1'


class ForchProxy():
    """Class that implements the module that creates a proxy server"""

    def __init__(self, proxy_config, content_type=None):
        self._proxy_config = proxy_config
        self._proxy_port = self._proxy_config.proxy_port or DEFAULT_PROXY_PORT
        self._pages = {}
        self._proxy_server = None
        self._content_type = content_type
        self._logger = get_logger('proxy')

    def start(self):
        """Start proxy server"""
        self._register_pages()
        self._proxy_server = HttpServer(self._proxy_port, content_type=self._content_type)
        try:
            self._proxy_server.map_request('', self._get_path_data)
        except Exception as e:
            self._proxy_server.map_request('', functools.partial(self._show_error, e))
        finally:
            threading.Thread(target=self._proxy_server.start_server(), daemon=True).start()
            self._logger.info('Started proxy server on port %s', self._proxy_port)

    def stop(self):
        """Kill server"""
        self._logger.info('Stopping proxy server')
        self._proxy_server.stop_server()

    def _get_url(self, server, port):
        return 'http://' + str(server) + ':' + str(port)

    def _register_page(self, path, server, port):
        self._pages[path] = self._get_url(server, port)

    def _register_pages(self):
        for name, target in self._proxy_config.targets.items():
            self._register_page(name, DEFAULT_SERVER_ADDRESS, target.port)

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
            with urllib.request.urlopen(url) as response:
                return response.read().decode('utf-8')
        except Exception as e:
            return 'Error retrieving data from url %s: %s' % (url, str(e))

    def _show_error(self, error, path, params):
        """Display errors"""
        return f'Error creating proxy server: {str(error)}'
