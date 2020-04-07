"""Faucet config file watcher"""

import hashlib
import logging

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

LOGGER = logging.getLogger('watcher')


class FileChangeWatcher:
    """Watch file changes in a directory"""
    def __init__(self, dir):
        self._observer = Observer()
        self._dir = dir
        self._watched_files = {}

    def start(self):
        """Start watcher"""
        file_modify_handler = FileModifyHandler(self._handle_file_modify)
        self._observer.schedule(file_modify_handler, self._dir)
        self._observer.start()

    def stop(self):
        """Stop watcher"""
        self._observer.stop()

    def register_file_callback(self, file_path, file_change_callback):
        """Register a file handler"""
        file_data = self._watched_files.setdefault(file_path, {})
        file_data['hash'] = self._get_file_hash(file_path)
        file_data['callback'] = file_change_callback

    def unregister_file_callback(self, file_path):
        """Unregister the handler for a file"""
        self._watched_files.pop(file_path)

    def unregister_file_callbacks(self, file_paths):
        """Unregister handlers for files"""
        for file_path in file_paths:
            self.unregister_file_callback(file_path)

    def _handle_file_modify(self, file_path):
        file_data = self._watched_files.get(file_path)
        if not file_data:
            return

        new_hash = self._get_file_hash(file_path)
        if new_hash == file_data['hash']:
            return
        file_data['hash'] = new_hash

        LOGGER.info('File "%s" is modified. Executing callback', file_path)

        file_data['callback'](file_path)

    def _get_file_hash(self, file_path):
        with open(file_path) as file:
            content = file.read()
            return hashlib.sha256(content.encode('utf-8')).hexdigest()


class FileModifyHandler(FileSystemEventHandler):
    """Handles file change event"""
    def __init__(self, on_modified_callback):
        self._on_modified_callback = on_modified_callback

    def on_modified(self, event):
        """when file is modified, check if file content has changed"""
        super(FileModifyHandler, self).on_modified(event)

        if event.is_directory:
            return

        self._on_modified_callback(event.src_path)
