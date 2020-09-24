"""Schedule heart beat with functions that have to be called in order"""

import threading

from forch.utils import get_logger

LOGGER = get_logger('heartbeat')


class HeartbeatScheduler:
    """Heart beat scheduler"""
    def __init__(self, interval_sec):
        self._interval_sec = interval_sec
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

        threading.Timer(self._interval_sec, self._periodic_task).start()

    def start(self):
        """Start periodic task"""
        self._run = True
        threading.Thread(target=self._periodic_task, daemon=True).start()

    def stop(self):
        """Stop periodic task"""
        self._run = False
