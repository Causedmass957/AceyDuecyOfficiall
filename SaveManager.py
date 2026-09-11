"""Single-slot save game.

Pause -> "Save & Quit" writes the current GameEngine to savegame.json.
The main menu shows a "Resume Game" button whenever that file exists;
loading it deletes the file so a stale state can never be resumed twice.
"""

import json
import os

from GameEngine import GameEngine

SAVE_PATH = "savegame.json"


def has_save():
    return os.path.exists(SAVE_PATH)


def write_save(engine):
    try:
        with open(SAVE_PATH, "w", encoding="utf-8") as fh:
            json.dump(engine.to_dict(), fh, indent=2)
        return True
    except OSError:
        return False


def load_engine():
    """Return a rebuilt GameEngine, or None if the save is missing / unreadable."""
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None

    try:
        return GameEngine.from_dict(data)
    except (KeyError, TypeError, ValueError):
        return None


def clear_save():
    try:
        os.remove(SAVE_PATH)
    except OSError:
        pass
