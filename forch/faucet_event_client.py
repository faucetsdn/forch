"""Simple client for working with the faucet event socket"""

import copy
import functools
import json
import logging
import os
import select
import socket
import threading
import time

from forch.utils import dict_proto

from forch.proto.faucet_event_pb2 import FaucetEvent, PortChange

LOGGER = logging.getLogger('fevent')

class FaucetEventClient():
    """A general client interface to the FAUCET event API"""

    FAUCET_RETRIES = 10
    _PORT_DEBOUNCE_SEC = 5

    def __init__(self, config):
        self.config = config
        self.sock = None
        self.buffer = None
        self._buffer_lock = threading.Lock()
        self._handlers = {}
        self.previous_state = None
        self._port_debounce_sec = config.port_debounce_sec or self._PORT_DEBOUNCE_SEC
        self._port_timers = {}
        self.event_socket_connected = False
        self._last_event_id = None

    def connect(self):
        """Make connection to sock to receive events"""

        sock_path = os.getenv('FAUCET_EVENT_SOCK')

        assert sock_path, 'Environment FAUCET_EVENT_SOCK not defined'

        self.previous_state = {}
        self.buffer = ''

        retries = self.FAUCET_RETRIES
        while not os.path.exists(sock_path):
            LOGGER.info('Waiting for socket path %s', sock_path)
            assert retries > 0, "Could not find socket path %s" % sock_path
            retries -= 1
            time.sleep(1)

        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.connect(sock_path)
            self.event_socket_connected = True
        except socket.error as err:
            self.event_socket_connected = False
            raise ConnectionError("Failed to connect because: %s" % err)

    def disconnect(self):
        """Disconnect this event socket"""
        if self.sock:
            self.sock.close()
        self.sock = None
        self.event_socket_connected = False
        with self._buffer_lock:
            self.buffer = None

    def register_handler(self, proto, handler):
        """Register an event handler for the given proto class"""
        message_name = self._convert_to_snake_caps(proto.__name__)
        LOGGER.info('Registering handler for event type %s', message_name)
        self._handlers[message_name] = handler

    def register_handlers(self, handlers):
        """Register a list of handler (proto, func) tuples"""
        for handler in handlers:
            self.register_handler(handler[0], handler[1])

    def _convert_to_snake_caps(self, name):
        return functools.reduce(lambda x, y: x + ('_' if y.isupper() else '') + y, name).upper()

    def has_data(self):
        """Check to see if the event socket has any data to read"""
        if self.sock:
            read, dummy_write, dummy_error = select.select([self.sock], [], [], 0)
            return read
        return False

    def has_event(self, blocking=False):
        """Check if there are any queued events"""
        while True:
            if self.buffer and '\n' in self.buffer:
                return True
            if self.sock and (blocking or self.has_data()):
                data = self.sock.recv(1024).decode('utf-8')
                if not data:
                    self.disconnect()
                    time.sleep(1)
                    return False
                with self._buffer_lock:
                    self.buffer += data
            else:
                return False

    def _valid_event_order(self, event):
        if event.get('debounced'):
            return True
        event_id = int(event['event_id'])
        assert self._last_event_id, '_last_event_id undefined, check for initialization errors'
        if event_id <= self._last_event_id:
            LOGGER.debug('Outdated faucet event #%d', event_id)
            return False
        self._last_event_id += 1
        if event_id != self._last_event_id:
            raise Exception('Out-of-sequence event id #%d' % event_id)
        return True

    def _handle_port_change_debounce(self, event, target_event):
        if isinstance(target_event, PortChange):
            dpid = target_event.dp_id
            port = target_event.port_no
            active = target_event.status and target_event.reason != 'DELETE'
            if not event.get('debounced'):
                self._debounce_port_event(event, port, active)
            elif self._process_state_update(dpid, port, active):
                return True
            return False
        return True

    def _handle_ports_status(self, event):
        (_, dpid, status) = self.as_ports_status(event)
        if dpid:
            for port in status:
                # Prepend events so they functionally replace the current one in the queue.
                self._prepend_event(event, self._make_port_change(port, status[port]))
            return False
        return True

    def _process_state_update(self, dpid, port, active):
        state_key = '%s-%d' % (dpid, port)
        if state_key in self.previous_state and self.previous_state[state_key] == active:
            return False
        LOGGER.debug('Port change %s active %s', state_key, active)
        self.previous_state[state_key] = active
        return True

    def _debounce_port_event(self, event, port, active):
        if not self._port_debounce_sec:
            self._handle_debounce(event, port, active)
            return
        state_key = '%s-%d' % (event['dp_id'], port)
        if state_key in self._port_timers:
            LOGGER.debug('Port cancel %s', state_key)
            self._port_timers[state_key].cancel()
        if active:
            self._handle_debounce(event, port, active)
            return
        LOGGER.debug('Port timer %s = %s', state_key, active)
        timer = threading.Timer(self._port_debounce_sec,
                                lambda: self._handle_debounce(event, port, active))
        timer.start()
        self._port_timers[state_key] = timer

    def _handle_debounce(self, event, port, active):
        LOGGER.debug('Port handle %s-%s as %s', event['dp_id'], port, active)
        self._append_event(event, self._make_port_change(port, active), debounced=True)

    def _merge_event(self, base, event, timestamp=None, debounced=None):
        merged_event = copy.deepcopy(event)
        merged_event.update({
            'dp_name': base['dp_name'],
            'dp_id': base['dp_id'],
            'event_id': base['event_id'],
            'time': timestamp if timestamp else base['time'],
            'debounced': debounced
        })
        return merged_event

    def _prepend_event(self, base, event):
        merged_event = self._merge_event(base, event)
        with self._buffer_lock:
            self.buffer = '%s\n%s' % (json.dumps(merged_event), self.buffer)

    def _append_event(self, base, event, debounced):
        event_str = json.dumps(self._merge_event(base, event, timestamp=time.time(),
                                                 debounced=debounced))
        with self._buffer_lock:
            index = self.buffer.rfind('\n')
            if index == len(self.buffer) - 1:
                self.buffer = '%s%s\n' % (self.buffer, event_str)
            elif index == -1:
                self.buffer = '%s\n%s' % (event_str, self.buffer)
            else:
                self.buffer = '%s\n%s%s' % (self.buffer[:index], event_str, self.buffer[index:])
            LOGGER.debug('appended %s\n%s*', event_str, self.buffer)

    def set_event_horizon(self, event_horizon):
        """Set the event horizon to throw away unnecessary events"""
        self._last_event_id = event_horizon
        LOGGER.info('Setting event horizon to event #%d', event_horizon)

    def _dispatch_faucet_event(self, target, target_event):
        if target in self._handlers:
            LOGGER.debug('dispatching %s event', target)
            self._handlers[target](target_event)
            return True
        return False

    def next_event(self, blocking=False):
        """Return the next event from the queue"""
        while self.event_socket_connected and self.has_event(blocking=blocking):
            with self._buffer_lock:
                line, remainder = self.buffer.split('\n', 1)
                self.buffer = remainder
            try:
                event = json.loads(line)
            except Exception as e:
                LOGGER.info('Error (%s) parsing\n%s*\nwith\n%s*', str(e), line, remainder)
                continue
            targets = list(t for t in self._handlers if t in event)
            event_target = targets[0] if targets else None
            faucet_event = dict_proto(event, FaucetEvent, ignore_unknown_fields=True)
            target_event = getattr(faucet_event, str(event_target), None)
            dispatch = self._valid_event_order(event) and target_event
            dispatch = dispatch and self._handle_port_change_debounce(event, target_event)
            dispatch = dispatch and self._handle_ports_status(event)
            if dispatch:
                self._augment_event_proto(faucet_event, target_event)
                if not self._dispatch_faucet_event(event_target, target_event):
                    return event
        return None

    def _augment_event_proto(self, event, target_event):
        target_event.timestamp = event.time
        if hasattr(target_event, 'dp_name'):
            target_event.dp_name = event.dp_name
        return target_event

    def _make_port_change(self, port, status):
        return {
            'PORT_CHANGE': {
                'port_no': port,
                'status': status,
                'reason': 'MODIFY'
            }
        }

    def _make_l2_learn(self, entry):
        return {
            'L2_LEARN': entry
        }

    def as_ports_status(self, event):
        """Convert the event to port status info, if applicable"""
        if not event or 'PORTS_STATUS' not in event:
            return (None, None, None)
        return (event['dp_name'], event['dp_id'], event['PORTS_STATUS'])
