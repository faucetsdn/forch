"""HTTP socket server interface"""

import functools
import http.server
import json
import os
import socketserver
import threading
import urllib

from google.protobuf.message import Message

from forch.utils import get_logger, proto_json


class HttpException(Exception):
    """Http exception base class"""
    def __init__(self, message, http_status):
        Exception.__init__(self, message)
        self.http_status = http_status


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Handle requests in a separate thread."""


class RequestHandler(http.server.BaseHTTPRequestHandler):
    """Handler for simple http requests"""

    def __init__(self, context, *args, **kwargs):
        self._context = context
        super().__init__(*args, **kwargs)
        self._logger = get_logger('httpserv')

    # pylint: disable=invalid-name
    def do_GET(self):
        """Handle a basic http request get method"""
        try:
            self._check_url()
            parsed = urllib.parse.urlparse(self.path)
            opts = {}
            opt_pairs = urllib.parse.parse_qsl(parsed.query)
            for pair in opt_pairs:
                opts[pair[0]] = pair[1]
            message = str(self._context.get_data(self.headers.get('Host'), parsed.path[1:], opts))
            self.send_response(http.HTTPStatus.OK)
            if self._context.content_type:
                self.send_header('Content-type', self._context.content_type)
            self.end_headers()
            self.wfile.write(message.encode())
        except HttpException as http_exception:
            self.send_response(http_exception.http_status)
            self.end_headers()
            self._logger.warning(http_exception)
        except Exception as exception:
            self.send_response(http.HTTPStatus.INTERNAL_SERVER_ERROR)
            self.end_headers()
            self._logger.error('Unhandled exception: %s', exception)

    def _check_url(self):
        """Check if url is illegal"""
        if not self.headers.get('Host'):
            raise HttpException(f'Host is empty. Path: {self.path}',
                                http.HTTPStatus.BAD_REQUEST)
        if not self.path:
            raise HttpException('Path is empty', http.HTTPStatus.BAD_REQUEST)
        if '..' in self.path:
            raise HttpException(f'Path contains directory traversal notations: {self.path}',
                                http.HTTPStatus.BAD_REQUEST)


class HttpServer():
    """Simple http server for managing simple requests"""

    _DEFAULT_FILE = 'index.html'

    def __init__(self, port, config=None, content_type=None):
        self._config = config
        self._paths = {}
        self._server = None
        self._root_path = config.http_root if config and config.http_root else 'public'
        self._port = port
        self._host = '0.0.0.0'
        self._thread = None
        self.content_type = content_type
        self._logger = get_logger('httpserv')

    def start_server(self):
        """Start serving thread"""
        self._logger.info('Starting http server on %s', self._get_url_base())
        address = (self._host, self._port)
        handler = functools.partial(RequestHandler, self)
        self._server = ThreadedHTTPServer(address, handler)

        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.deamon = False
        self._thread.start()

    def join_thread(self):
        """Join http server thread"""
        self._thread.join()

    def _get_url_base(self):
        return 'http://%s:%s' % (self._host, self._port)

    def stop_server(self):
        """Stop and clean up server"""
        self._logger.info("Stopping server.")
        self._server.server_close()
        self._server.shutdown()

    def map_request(self, path, target):
        """Register a request mapping"""
        self._paths[path] = target

    def get_data(self, host, path, params):
        """Get data for a particular request path and query params"""
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
        try:
            content = self.read_file(full_path)
            return content
        except Exception as http_exception:
            raise HttpException(str(http_exception),
                                http.HTTPStatus.BAD_REQUEST) from http_exception


    def static_file(self, base_path):
        """Map a static file handler to a simple request"""
        return lambda req_path, params: self._split_request(base_path, req_path)
