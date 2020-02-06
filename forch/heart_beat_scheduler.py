"""Schedule heart beat with functions that have to be called in order"""
import logging
import threading

LOGGER = logging.getLogger('HeartBeat')


class HeartBeatScheduler:
    """Heart beat scheduler"""
    def __init__(self, interval):
        self._interval = interval
        self._callbacks = []

    def add_callback(self, callback):
        self._callbacks.append(callback)

    def _periodic_task(self):
        for callback in self._callbacks:
            try:
                callback()
            except Exception as error:
                LOGGER.error("Running %s: %s", callback, error)

        threading.Timer(self._interval, self._periodic_task).start()

    def start(self):
        """Start periodic task"""
        threading.Thread(target=self._periodic_task).start()
