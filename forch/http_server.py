"""HTTP socket server interface"""

import functools
import http.server
import json
import logging
import os
import socketserver
import threading
import urllib

from google.protobuf.message import Message

from forch.utils import proto_json

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
        url_error = self._check_url()
        if url_error:
            self.send_response(500)
            self.end_headers()
            LOGGER.warning(url_error)
            return
        self.send_response(200)
        self.end_headers()
        parsed = urllib.parse.urlparse(self.path)
        opts = {}
        opt_pairs = urllib.parse.parse_qsl(parsed.query)
        for pair in opt_pairs:
            opts[pair[0]] = pair[1]
        message = str(self._context.get_data(self.headers.get('Host'), parsed.path[1:], opts))
        self.wfile.write(message.encode())

    def _check_url(self):
        """Check if url is illegal"""
        if not self.headers.get('Host'):
            return f'Host is empty. Path: {self.path}'
        if not self.path:
            return f'Path is empty'
        if '..' in self.path:
            print(self.path)
            return f'Path contains directory traversal notations: {self.path}'
        return None


class HttpServer():
    """Simple http server for managing simple requests"""

    _DEFAULT_FILE = 'index.html'

    def __init__(self, config, port):
        self._config = config
        self._paths = {}
        self._server = None
        self._root_path = config.get('http_root', 'public')
        self._port = port
        self._host = '0.0.0.0'
        self._thread = None

    def start_server(self):
        """Start serving thread"""
        LOGGER.info('Starting http server on %s', self._get_url_base())
        address = (self._host, self._port)
        handler = functools.partial(RequestHandler, self)
        self._server = ThreadedHTTPServer(address, handler)

        self._thread = threading.Thread(target=self._server.serve_forever)
        self._thread.deamon = False
        self._thread.start()

    def join_thread(self):
        """Join http server thread"""
        self._thread.join()

    def _get_url_base(self):
        return 'http://%s:%s' % (self._host, self._port)

    def stop_server(self):
        """Stop and clean up server"""
        LOGGER.info("Stopping server.")
        self._server.server_close()
        self._server.shutdown()

    def map_request(self, path, target):
        """Register a request mapping"""
        self._paths[path] = target

    def get_data(self, host, path, params):
        """Get data for a particular request path and query params"""
        try:
            for a_path in self._paths:
                if path.startswith(a_path):
                    full_path = host + '/' + path
                    result = self._paths[a_path](full_path, params)
                    if isinstance(result, (bytes, str)):
                        return result
                    if isinstance(result, Message):
                        return proto_json(result)
                    return json.dumps(result)
            return str(self._paths)
        except Exception as e:
            LOGGER.exception('Handling request %s: %s', path, str(e))

    def read_file(self, full_path):
        """Read a file and return the entire contents"""
        binary = full_path.endswith('.ico')
        mode = 'rb' if binary else 'r'
        with open(full_path, mode) as in_file:
            return in_file.read()

    def _split_request(self, base_path, req_path):
        slash = req_path.find('/') + 1
        path = req_path[slash:]
        full_path = os.path.join(self._root_path, path)
        if os.path.isdir(full_path):
            full_path = os.path.join(full_path, self._DEFAULT_FILE)
        return self.read_file(full_path)

    def static_file(self, base_path):
        """Map a static file handler to a simple request"""
        return lambda req_path, params: self._split_request(base_path, req_path)
