"""Faucet config file watcher"""

import os

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import forch.faucetizer


class FaucetConfigFileWatcher:
    """Watch file changes"""
    def __init__(self, structural_config_file, faucetizer):
        self._observer = Observer()
        handler = FaucetConfigFileHandler(faucetizer, structural_config_file)
        self._observer.schedule(handler, os.path.dirname(structural_config_file))

    def start(self):
        """Start watcher"""
        self._observer.start()

    def stop(self):
        """Stop watcher"""
        self._observer.stop()


class FaucetConfigFileHandler(FileSystemEventHandler):
    """Handles config file changes"""
    def __init__(self, faucetizer, structural_config_file):
        self._faucetizer = faucetizer
        self._structural_config_file = structural_config_file

    def on_modified(self, event):
        """on file modified, update faucet config in faucetizer"""
        super(FaucetConfigFileHandler, self).on_modified(event)

        if event.is_directory or self._structural_config_file != event.src_path:
            return

        forch.faucetizer.update_structural_config(self._faucetizer, self._structural_config_file)