"""Persistent user settings.

Only a small set today (fullscreen), but the file and the Settings screen are
structured so more options can be added over time without further plumbing.
"""

import json
import os

SETTINGS_PATH = "settings.json"

DEFAULTS = {
    "fullscreen": False,
    "window_size": [1200, 800],
}

# Minimum size the resizable window is allowed to shrink to.
MIN_WINDOW_SIZE = (900, 600)


class Settings:
    def __init__(self, path=SETTINGS_PATH):
        self.path = path
        self.data = dict(DEFAULTS)
        self.load()

    def load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                stored = json.load(fh)
        except (OSError, ValueError):
            return
        if isinstance(stored, dict):
            for key in DEFAULTS:
                if key in stored:
                    self.data[key] = stored[key]

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, indent=2)
        except OSError:
            pass

    def get(self, key):
        return self.data.get(key, DEFAULTS.get(key))

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def toggle(self, key):
        self.set(key, not bool(self.get(key)))
        return self.get(key)
