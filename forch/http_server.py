"""HTTP socket server interface"""

import functools
import http.server
import json
import logging
import os
import socketserver
import threading
import urllib


LOGGER = logging.getLogger('httpserv')


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Handle requests in a separate thread."""


class RequestHandler(http.server.BaseHTTPRequestHandler):
    """Handler for simple http requests"""

    def __init__(self, context, *args, **kwargs):
        self._context = context
        super().__init__(*args, **kwargs)

    # pylint: disable=invalid-name
    def do_GET(self):
        """Handle a basic http request get method"""
        self.send_response(200)
        self.end_headers()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path[1:]
        opts = {}
        opt_pairs = urllib.parse.parse_qsl(parsed.query)
        for pair in opt_pairs:
            opts[pair[0]] = pair[1]
        message = str(self._context.get_data(path, opts))
        self.wfile.write(message.encode())


class HttpServer():
    """Simple http server for managing simple requests"""

    _DEFAULT_FILE = 'index.html'

    def __init__(self, config):
        self._config = config
        self._paths = {}
        self._server = None
        self._root_path = config.get('http_root', 'forch_public')

    def start_server(self):
        """Start serving thread"""
        address = ('0.0.0.0', 9019)
        LOGGER.info('Starting http server on http://%s:%s', address[0], address[1])
        handler = functools.partial(RequestHandler, self)
        self._server = ThreadedHTTPServer(address, handler)

        thread = threading.Thread(target=self._server.serve_forever)
        thread.deamon = False
        thread.start()

    def stop_server(self):
        """Stop and clean up server"""
        LOGGER.info("Stopping server.")
        self._server.server_close()
        self._server.shutdown()

    def map_request(self, path, target):
        """Register a request mapping"""
        self._paths[path] = target

    def get_data(self, request_path, params):
        """Get data for a particular request path and query params"""
        try:
            for a_path in self._paths:
                if request_path.startswith(a_path):
                    path_remain = request_path[len(a_path):]
                    result = self._paths[a_path](path_remain, params)
                    return result if isinstance(result, str) else json.dumps(result)
            return str(self._paths)
        except Exception as e:
            LOGGER.exception('Handling request %s: %s', request_path, str(e))

    def read_file(self, path, ext_path):
        """Read a file based on some path munging and return the entire contents"""
        full_path = os.path.join(self._root_path, path)
        if ext_path:
            full_path = os.path.join(full_path, ext_path)
        if os.path.isdir(full_path):
            full_path = os.path.join(full_path, self._DEFAULT_FILE)
        with open(full_path, 'r') as in_file:
            return in_file.read()

    def static_file(self, path):
        """Map a static file handler to a simple request"""
        return lambda path_remain, params: self.read_file(path, path_remain)
