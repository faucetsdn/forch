"""Schedule heart beat with functions that have to be called in order"""

import logging
import threading

LOGGER = logging.getLogger('heartbeat')


class HeartbeatScheduler:
    """Heart beat scheduler"""
    def __init__(self, interval):
        self._interval = interval
        self._callbacks = []
        self._run = False

    def add_callback(self, callback):
        """Add callback"""
        self._callbacks.append(callback)

    def _periodic_task(self):
        if not self._run:
            return

        for callback in self._callbacks:
            try:
                callback()
            except Exception as error:
                LOGGER.error("Error in running %s: %s", callback, error)

        threading.Timer(self._interval, self._periodic_task).start()

    def start(self):
        """Start periodic task"""
        self._run = True
        threading.Thread(target=self._periodic_task).start()

    def stop(self):
        """Stop periodic task"""
        self._run = False
