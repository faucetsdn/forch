"""Faucet config file watcher"""

import hashlib
import logging

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

LOGGER = logging.getLogger('watcher')


class FileChangeWatcher:
    """Watch file changes"""
    def __init__(self, path):
        self._observer = Observer()
        self._watches = {}
        self._path = path

    def start(self):
        """Start watcher"""
        self._observer.start()

    def stop(self):
        """Stop watcher"""
        self._observer.stop()

    def register_file_handler(self, file_path, on_modified_callback):
        """Register a file handler"""
        file_handler = FileChangeHandler(file_path, on_modified_callback)
        self._watches[file_path] = self._observer.schedule(file_handler, self._path)

    def unregister_file_handler(self, file_path):
        """Unregister the handler for a file"""
        if file_path in self._watches:
            self._observer.unschedule(self._watches[file_path])

    def unregister_file_handlers(self, file_paths):
        """Unregister handlers for files"""
        for file_path in file_paths:
            self.unregister_file_handler(file_path)


class FileChangeHandler(FileSystemEventHandler):
    """Handles file change event"""
    def __init__(self, file, on_modified_callback):
        self._file = file
        self._last_hash = self._get_file_hash()
        self._on_modified_callback = on_modified_callback

    def on_modified(self, event):
        """when file is modified, check if file content has changed"""
        super(FileChangeHandler, self).on_modified(event)

        if event.is_directory or self._file != event.src_path:
            return

        new_hash = self._get_file_hash()
        if new_hash == self._last_hash:
            return
        self._last_hash = new_hash

        LOGGER.info('File "%s" is modified', event.src_path)

        self._on_modified_callback(event.src_path)

    def _get_file_hash(self):
        with open(self._file) as file:
            content = file.read()
            return hashlib.sha256(content.encode('utf-8')).hexdigest()
