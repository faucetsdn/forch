"""Faucet config file watcher"""

import hashlib
import logging
import os
import yaml

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

LOGGER = logging.getLogger('watcher')


class ConfigFileWatcher:
    """Watch file changes"""
    def __init__(self, structural_config_file, faucetizer):
        self._observer = Observer()
        self._structural_config_file = structural_config_file
        self._faucetizer = faucetizer
        self._path = os.path.dirname(structural_config_file)
        self._acl_watches = []
        faucet_config_handler = FaucetConfigFileHandler(
            faucetizer, structural_config_file, self._reschedule_acl_file_handlers)
        self._observer.schedule(faucet_config_handler, self._path)
        self._reschedule_acl_file_handlers()

    def start(self):
        """Start watcher"""
        self._observer.start()

    def stop(self):
        """Stop watcher"""
        self._observer.stop()

    def _reschedule_acl_file_handlers(self):
        for watch in self._acl_watches:
            self._observer.unschedule(watch)

        self._acl_watches = []
        with open(self._structural_config_file) as file:
            structural_config = yaml.safe_load(file)
            for acl_config_file in structural_config.get('include', []):
                acl_config_handler = AclConfigFileHandler(self._faucetizer, acl_config_file)
                watch = self._observer.schedule(acl_config_handler, self._path)
                self._acl_watches.append(watch)


class ConfigFileHandler(FileSystemEventHandler):
    """Handles file change event"""
    def __init__(self, config_file):
        self._config_file = config_file
        self._last_hash = None

    def on_modified(self, event):
        """when file is modified"""
        super(FileSystemEventHandler, self).on_modified(event)
        if event.is_directory or self._config_file != event.src_path:
            return

        with open(self._config_file) as file:
            content = file.read()
            if not content:
                return

            hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            if hash == self._last_hash:
                return

            self._last_hash = hash

        self._on_modified()

    def _on_modified(self):
        pass


class FaucetConfigFileHandler(ConfigFileHandler):
    """Handles Faucet config file changes"""
    def __init__(self, faucetizer, structural_config_file, structural_config_handler):
        super(FaucetConfigFileHandler, self).__init__(structural_config_file)
        self._faucetizer = faucetizer
        self._structural_config_handler = structural_config_handler

    def _on_modified(self):
        """on Faucet file modified, update faucet config in faucetizer"""
        self._faucetizer.reload_structural_config()
        self._structural_config_handler()


class AclConfigFileHandler(ConfigFileHandler):
    """Handles ACL config file changes"""
    def __init__(self, faucetizer, acl_config_file):
        super(ConfigFileHandler, self).__init__(acl_config_file)
        self._faucetizer = faucetizer

    def _on_modified(self):
        """On ACL config file modified, reprocess ACL config in faucetizer"""
        self._faucetizer.reload_acl_file(self._config_file)
