"""Faucet event tests"""

import functools
import json
import os
import socket
import threading
import unittest

from unit_base import ForchestratorTestBase


class FaucetEventOrderTestCase(ForchestratorTestBase):
    """Faucet event order test case"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = threading.Lock()
        self._event_server_thread = None
        self._forchestrator_thread = None
        self._event_server_connection = None

    def _handle_connection(self, event_socket):
        event_socket.listen(1)
        while True:
            print('Waiting for incoming connection')
            self._connection, _ = event_socket.accept()

    def _setup_event_server(self):
        assert self._temp_socket_file
        event_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        event_socket.bind(self._temp_socket_file)
        handle_connection = functools.partial(self._handle_connection, event_socket)
        self._event_server_thread = threading.Thread(target=handle_connection, daemon=True)

    def setUp(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setup_event_server()

    def test_out_of_sequence(self):
        events = [
            {'version': 1, 'time': 123.0, 'event_id': 101},
            {'version': 1, 'time': 124.0, 'event_id': 200},
        ]
        for event in events:
            event_bytes = bytes('\n'.join((json.dumps(event, default=str), '')).encode('UTF-8'))
            self._event_server_connection.sendall(event_bytes)

if __name__ == '__main__':
    unittest.main()
