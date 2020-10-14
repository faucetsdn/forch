"""Faucet event tests"""

import functools
import json
import os
import socket
import threading
import unittest

from forch.utils import MetricsFetchingError

from unit_base import ForchestratorTestBase


class FaucetEventOrderTestCase(ForchestratorTestBase):
    """Faucet event order test case"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = threading.Lock()
        self._event_server_thread = None

    def _handle_connection(self, event_socket):
        event_socket.listen(1)
        print('Waiting for incoming connection')
        connection, _ = event_socket.accept()

        events = [
            {'version': 1, 'time': 123.0, 'event_id': 101},
            {'version': 1, 'time': 124.0, 'event_id': 200},
        ]
        for event in events:
            print(f'Sending event: {event}')
            event_bytes = bytes('\n'.join((json.dumps(event, default=str), '')).encode('UTF-8'))
            connection.sendall(event_bytes)

        connection.recv(16)

    def _setup_event_server(self):
        assert self._temp_socket_file
        event_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        print(f'Binding socket on {self._temp_socket_file}')
        event_socket.bind(self._temp_socket_file)
        handle_connection = functools.partial(self._handle_connection, event_socket)
        self._event_server_thread = threading.Thread(target=handle_connection, daemon=True)
        self._event_server_thread.start()

    # pylint: disable=invalid-name
    def setUp(self, *args, **kwargs):
        """Set up env and event server"""
        try:
            super().setUp(*args, **kwargs)
        except MetricsFetchingError as error:
            print(f'Expected error during Forchestrator initialization: %s', error)
        os.environ['FAUCET_EVENT_DEBUG'] = '1'
        self._setup_event_server()

    # pylint: disable=protected-access
    def test_out_of_sequence(self):
        """Test Forch behavior in case of out-of-sequence event"""
        self._forchestrator._faucet_events_connect()
        self._forchestrator._faucet_events.set_event_horizon(100)
        restore_states_called = False

        try:
            self._forchestrator.main_loop()
        except MetricsFetchingError as error:
            # Forchestrator.restore_states() will raise VarzFetchingError as Faucet prometheus
            # client is not enabled, and thus this error implies restore_states() is called.
            print(f'Expected error during restoring states: {error}')
            restore_states_called = True

        self.assertTrue(restore_states_called)
        self.assertEqual(self._forchestrator._faucet_events._last_event_id, 102)


if __name__ == '__main__':
    unittest.main()
