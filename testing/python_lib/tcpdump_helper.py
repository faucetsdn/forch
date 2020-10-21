"""Helper class for working with tcpdump."""

import errno
import fcntl
import subprocess
import os
import re

import logging


class TcpdumpHelper:
    """Run tcpdump on interface, then a list of functions, and return tcpdump's parsed output."""

    pipe = None
    started = False
    last_line = None
    funcs = None
    readbuf = None
    blocking = True

    # pylint: disable=too-many-arguments
    def __init__(self, intf_name, tcpdump_filter=None, funcs=None, docker_host=None,
                 vflags='-v', timeout=10, packets=2, root_intf=False,
                 pcap_out=None, blocking=True):
        self.devnull = open(os.devnull, 'wb')
        self.intf_name = intf_name
        self.funcs = funcs
        if root_intf:
            self.intf_name = self.intf_name.split('.')[0]

        tcpdump_flags = vflags
        tcpdump_flags += ' -Z root'
        tcpdump_flags += ' -c %u' % packets if packets else ''
        tcpdump_flags += ' -w %s' % pcap_out if pcap_out else ''
        tcpdump_cmd = 'tcpdump -i %s %s --immediate-mode -e -n -U ' % (
            self.intf_name, tcpdump_flags)
        if tcpdump_filter:
            tcpdump_cmd += tcpdump_filter
        pipe_cmd = tcpdump_cmd
        if timeout:
            pipe_cmd = self.timeout_soft_cmd(tcpdump_cmd, timeout)

        if docker_host:
            pipe_cmd = ('docker exec %s ' % docker_host) + pipe_cmd

        pipe_cmd = pipe_cmd.split() if isinstance(pipe_cmd, str) else pipe_cmd

        logging.debug(pipe_cmd)
        self.pipe = subprocess.Popen(
            pipe_cmd,
            stdin=self.devnull,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            close_fds=True,
            shell=False)

        if self.stream():
            logging.debug('tcpdump_helper stream fd %s %s', self.stream().fileno(), self.intf_name)
        self.readbuf = ''
        self.set_blocking(blocking)

    def __del__(self):
        self.devnull.close()

    def stream(self):
        """Return pipe's STDOUT, or None."""
        if self.pipe:
            return self.pipe.stdout
        return None

    def set_blocking(self, blocking=True):
        """Set blocking on pipe's STDOUT."""
        stdout_fd = self.pipe.stdout.fileno()
        flags = fcntl.fcntl(stdout_fd, fcntl.F_GETFL)
        self.blocking = blocking
        if blocking:
            flags = flags & ~os.O_NONBLOCK
        else:
            flags = flags | os.O_NONBLOCK
        fcntl.fcntl(stdout_fd, fcntl.F_SETFL, flags)

    def execute(self):
        """Run the helper and accumulate tcpdump output."""
        tcpdump_txt = ''
        if self.stream():
            while True:
                line = self.next_line()
                if not line:
                    break
                logging.debug('tcpdump_helper fd %d line "%s"', self.stream().fileno(), line)
                tcpdump_txt += line.strip()
        return tcpdump_txt

    def terminate(self):
        """Terminate the helper."""
        if not self.pipe or not self.stream():
            return -1

        try:
            logging.debug('tcpdump_helper terminate fd %s', self.stream().fileno())
            self.pipe.terminate()
            result = self.pipe.wait()
            if result == 124:
                # Mask valid result from timeout command.
                result = 0
            self.pipe.stdout.close()
            self.pipe = None
            return result
        except EnvironmentError as err:
            logging.error('Error closing tcpdump_helper fd %d: %s', self.pipe.stdout.fileno(), err)
            return -2

    def readline(self):
        """Replacement readline() because built-in doesn't work with non-blocking IO"""
        fileno = self.pipe.stdout.fileno()
        while '\n' not in self.readbuf:
            try:
                read = os.read(fileno, 2**10)
            except OSError as err:
                if err.errno != errno.EAGAIN or not self.blocking:
                    raise
                continue
            if not read:
                line = self.readbuf
                self.readbuf = ''
                return line
            self.readbuf += read.decode()
        pos = self.readbuf.find('\n') + 1
        line = self.readbuf[0:pos]
        self.readbuf = self.readbuf[pos:]
        return line

    def next_line(self):
        """Retrieve next line from helper."""
        while True:
            try:
                line = self.readline()
            except OSError as err:
                if err.errno == errno.EWOULDBLOCK or err.errno == errno.EAGAIN:
                    return ''
                raise
            assert line or self.started, 'tcpdump did not start: %s' % self.last_line.strip()
            if self.started:
                return line
            if re.search('listening on %s' % self.intf_name, line):
                self.started = True
                # When we see tcpdump start, then call provided functions.
                if self.funcs is not None:
                    for func in self.funcs:
                        func()
            else:
                self.last_line = line

    def timeout_soft_cmd(self, cmd, timeout):
        """Same as timeout_cmd buf using SIGTERM on timeout."""
        return 'timeout %us stdbuf -o0 -e0 %s' % (timeout, cmd)
