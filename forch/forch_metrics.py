import forch.http_server
import functools

class ForchMetrics():
    def __init__(self, local_port, config):
        self._local_port = local_port
        self._config = config
        self._http_server = None
        self._metrics = None

    def start(self):
        self._http_server = forch.http_server.HttpServer(self._config, self._local_port)
        try:
            self._http_server.map_request('', self.get_metrics)
        except Exception as e:
            self._http_server.map_request('', functools.partial(show_error, e))
        finally:
            self._http_server.start_server()

    def stop(self):
        self._http_server.stop_server()

    def get_metrics(self, path, params):
        #return self._metrics
        return "Version 1"

