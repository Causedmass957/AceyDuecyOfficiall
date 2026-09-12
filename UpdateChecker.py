"""Checks GitHub Releases for a version newer than the one baked into this build.

Never auto-downloads or auto-replaces the running exe or its files -- this
follows the same "detect, don't silently install" convention as
TailscaleCheck.py. On finding a newer release it only hands back the tag and
the release page URL so the caller can show a "new version available" prompt
with a link; the player always clicks through themselves.

Every network call is wrapped so failure (offline, GitHub down, rate limited)
degrades to "no update info right now" rather than raising -- this must never
block or crash startup.
"""
import json
import urllib.error
import urllib.request

from Paths import resource_path

REPO = "Causedmass957/AceyDuecyOfficiall"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
TIMEOUT = 3.0


def current_version():
    """Version baked into this build via the VERSION file (bundled by PyInstaller)."""
    try:
        with open(resource_path("VERSION"), "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "0.0.0"


def _parse(version_string):
    """'v1.2.3' / '1.2.3-beta1' -> (1, 2, 3) for comparison. Ignores prerelease suffix."""
    core = version_string.strip().lstrip("vV").split("-")[0]
    parts = []
    for piece in core.split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def check_for_update():
    """Return (latest_tag, release_url) if GitHub has a newer release, else None.

    Never raises. Safe to call from a background thread at startup.
    """
    try:
        request = urllib.request.Request(
            API_URL,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "AceyDuecy-UpdateCheck"},
        )
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            data = json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None

    tag = data.get("tag_name") or ""
    url = data.get("html_url") or f"https://github.com/{REPO}/releases/latest"
    if not tag:
        return None

    if _parse(tag) > _parse(current_version()):
        return tag, url
    return None
