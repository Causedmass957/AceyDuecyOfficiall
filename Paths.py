"""Filesystem locations for bundled assets and per-user writable data.

Two different needs, two different rules:

- resource_path(): read-only files shipped WITH the game (images, sounds,
  fonts). In dev these live next to the source; a PyInstaller build unpacks
  them into a temp/bundle folder pointed to by sys._MEIPASS. Resolve
  through this helper instead of a bare relative path so both cases work
  and future sound files just follow the same pattern splash.jpg already
  hinted at.

- data_dir() / data_path(): per-user files the game WRITES (profile/stats
  db, settings, save game, crash log). These must never live next to the
  exe -- a normal install (e.g. Program Files) usually isn't writable by a
  normal user, and cwd is unpredictable when launched by double-click.
  They live under %APPDATA%\\AceyDuecy instead, optionally namespaced by
  channel so a beta build's save data can't collide with production's on
  the same test machine.
"""
import os
import sys

_APP_NAME = "AceyDuecy"

# Directory the source files live in (== bundle root once frozen; PyInstaller
# extracts to sys._MEIPASS and that's where --add-data assets land).
_SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))


def resource_path(*parts):
    """Absolute path to a bundled, read-only asset (image, sound, font)."""
    base = getattr(sys, "_MEIPASS", _SOURCE_DIR)
    return os.path.join(base, *parts)


def _bundled_channel():
    """Read a build-time CHANNEL file, if the release pipeline stamped one in.

    dev/staging builds get one written next to VERSION (see
    .github/workflows/dev-build.yml and release.yml); a normal production
    build and every local dev run have no such file, which means "no
    namespacing" -- the plain %APPDATA%\\AceyDuecy folder.
    """
    try:
        with open(resource_path("CHANNEL"), "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


# Separates save data for side-by-side installs (dev / beta / production) on
# one machine, so a beta tester's game doesn't corrupt production save data
# sitting on the same PC. An env var always wins, for ad-hoc dev/test
# overrides (see conftest.py, test_lan.py); otherwise fall back to whatever
# channel the build was stamped with.
APP_CHANNEL = os.environ.get("ACEYDUECY_CHANNEL", "") or _bundled_channel()


def data_dir():
    """Per-user writable folder for saves / settings / stats / crash log."""
    root = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(root, _APP_NAME, APP_CHANNEL) if APP_CHANNEL else os.path.join(root, _APP_NAME)
    os.makedirs(folder, exist_ok=True)
    return folder


def data_path(filename):
    return os.path.join(data_dir(), filename)


def migrate_legacy_file(filename):
    """Move a pre-existing cwd-relative file into data_dir(), once.

    Older builds wrote stats.db / settings.json / savegame.json next to the
    source. Without this, switching to data_dir() would look like existing
    profiles/stats/settings vanished the first time this runs. Safe to call
    on every startup -- it's a no-op once the file has already moved (or
    never existed).
    """
    new_path = data_path(filename)
    if os.path.exists(new_path):
        return new_path
    legacy_path = os.path.join(_SOURCE_DIR, filename)
    if os.path.exists(legacy_path):
        try:
            os.replace(legacy_path, new_path)
        except OSError:
            pass
    return new_path
