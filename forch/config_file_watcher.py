"""Faucet config file watcher"""

import hashlib
import logging
import os

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

LOGGER = logging.getLogger('watcher')


class ConfigFileWatcher:
    """Watch file changes"""
    def __init__(self, structural_config_file, structural_config_modified_callback):
        self._observer = Observer()
        self._structural_config_file = structural_config_file
        self._path = os.path.dirname(structural_config_file)
        self._acl_watches = {}
        structural_config_handler = ConfigFileHandler(
            self._structural_config_file, structural_config_modified_callback)
        self._observer.schedule(structural_config_handler, self._path)

    def start(self):
        """Start watcher"""
        self._observer.start()

    def stop(self):
        """Stop watcher"""
        self._observer.stop()

    def schedule_acl_file_handler(self, acl_file_name, on_modified_callback):
        """Schedule a handler for file"""
        acl_file_path = os.path.join(self._path, acl_file_name)
        file_handler = ConfigFileHandler(acl_file_path, on_modified_callback)
        self._acl_watches[acl_file_name] = self._observer.schedule(file_handler, acl_file_path)

    def unschedule_acl_watches(self):
        """Unschedule watches"""
        for watch in self._acl_watches:
            self._observer.unschedule(watch)


class ConfigFileHandler(FileSystemEventHandler):
    """Handles file change event"""
    def __init__(self, config_file, on_modified_callback):
        self._config_file = config_file
        self._last_hash = self._get_file_hash()
        self._on_modified_callback = on_modified_callback

    def on_modified(self, event):
        """when file is modified, check if file content has changed"""
        super(FileSystemEventHandler, self).on_modified(event)

        if event.is_directory or self._config_file != event.src_path:
            return

        new_hash = self._get_file_hash()
        if new_hash == self._last_hash:
            return
        self._last_hash = new_hash

        LOGGER.info('File "%s" is modified', event.src_path)

        self._on_modified_callback()

    def _get_file_hash(self):
        with open(self._config_file) as file:
            content = file.read()
            return hashlib.sha256(content.encode('utf-8')).hexdigest()
