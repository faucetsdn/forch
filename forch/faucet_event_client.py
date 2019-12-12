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

from forch.proto.faucet_event_pb2 import FaucetEvent

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
        self._port_debounce_sec = int(config.get('port_debounce_sec', self._PORT_DEBOUNCE_SEC))
        self._port_timers = {}
        self.event_socket_connected = False

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

    def _filter_faucet_event(self, event):
        (name, dpid, port, active) = self.as_port_state(event)
        if dpid and port:
            if not event.get('debounced'):
                self._debounce_port_event(event, port, active)
            elif self._process_state_update(dpid, port, active):
                return True
            return False

        (name, dpid, status) = self.as_ports_status(event)
        if dpid:
            for port in status:
                # Prepend events so they functionally replace the current one in the queue.
                self._prepend_event(event, self._make_port_state(port, status[port]))
            return False
        (name, macs) = self._as_learned_macs(event)
        if name:
            for mac in macs:
                self._prepend_event(event, self._make_l2_learn(mac))
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
        self._append_event(event, self._make_port_state(port, active), debounced=True)

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

    def _dispatch_faucet_event(self, event):
        for target in self._handlers:
            if target in event:
                faucet_event = dict_proto(event, FaucetEvent)
                target_event = getattr(faucet_event, target)
                self._augment_event_proto(faucet_event, target_event)
                LOGGER.info('dispatching %s event', target)
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
            if self._filter_faucet_event(event):
                if not self._dispatch_faucet_event(event):
                    return event
        return None

    def _augment_event_proto(self, event, target_event):
        target_event.timestamp = event.time
        if hasattr(target_event, 'dp_name'):
            target_event.dp_name = event.dp_name
        return target_event

    # pylint: disable=too-many-arguments
    def _make_port_state(self, port, status):
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

    def as_config_change(self, event):
        """Convert the event to dp change info, if applicable"""
        if not event or 'CONFIG_CHANGE' not in event:
            return (None, None, None, None)
        restart_type = event['CONFIG_CHANGE'].get('restart_type')
        config_hash_info = event['CONFIG_CHANGE'].get('config_hash_info')
        return (event['dp_name'], event['dp_id'], restart_type, config_hash_info)

    def as_ports_status(self, event):
        """Convert the event to port status info, if applicable"""
        if not event or 'PORTS_STATUS' not in event:
            return (None, None, None)
        return (event['dp_name'], event['dp_id'], event['PORTS_STATUS'])

    def _as_learned_macs(self, event):
        """Convert the event to learned macs info, if applicable"""
        if not event or 'L2_LEARNED_MACS' not in event:
            return (None, None)
        return (event.get('dp_name'), event.get('L2_LEARNED_MACS'))

    def as_lag_state(self, event):
        """Convert event to lag status, if applicable"""
        if not event or 'LAG_CHANGE' not in event:
            return (None, None, None)
        port = event['LAG_CHANGE']['port_no']
        state = event['LAG_CHANGE']['state']
        return (event['dp_name'], port, state)

    def as_port_state(self, event):
        """Convert event to a port state info, if applicable"""
        if not event or 'PORT_CHANGE' not in event:
            return (None, None, None, None)
        name = event['dp_name']
        dpid = event['dp_id']
        port_no = int(event['PORT_CHANGE']['port_no'])
        reason = event['PORT_CHANGE']['reason']
        port_active = event['PORT_CHANGE']['status'] and reason != 'DELETE'
        return (name, dpid, port_no, port_active)

    def as_port_learn(self, event):
        """Convert to port learning info, if applicable"""
        if not event or 'L2_LEARN' not in event:
            return (None, None, None, None, None)
        name = event['dp_name']
        dpid = event['dp_id']
        port_no = int(event['L2_LEARN']['port_no'])
        eth_src = event['L2_LEARN']['eth_src']
        src_ip = event['L2_LEARN']['l3_src_ip']
        return (name, dpid, port_no, eth_src, src_ip)

    def as_stack_state(self, event):
        """Convert to stack link state info."""
        if not event or 'STACK_STATE' not in event:
            return (None, None, None)
        name = event['dp_name']
        port = event['STACK_STATE']['port']
        state = event['STACK_STATE']['state']
        return (name, port, state)

    def as_dp_change(self, event):
        """Convert to dp status"""
        if not event or 'DP_CHANGE' not in event:
            return (None, None)
        name = event['dp_name']
        connected = (event['DP_CHANGE']['reason'] == 'cold_start')
        return (name, connected)
