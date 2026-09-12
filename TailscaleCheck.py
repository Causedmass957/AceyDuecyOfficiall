"""Detects whether Tailscale is installed, without ever installing or bundling it.

Online (non-LAN) multiplayer needs Tailscale running on both machines. Per
the project's explicit decision (see the packaging-plan project memory):
this game never redistributes or silently installs a third party's binary.
It only detects presence and, if missing, hands the player a link to install
it themselves -- the same pattern old multiplayer games used for a missing
prerequisite like DirectX or .NET.
"""
import os
import shutil
import webbrowser

DOWNLOAD_URL = "https://tailscale.com/download/windows"

# Fallback for machines where Tailscale isn't on PATH but is installed.
_KNOWN_INSTALL_PATHS = [
    r"C:\Program Files\Tailscale\tailscale.exe",
    r"C:\Program Files (x86)\Tailscale\tailscale.exe",
]


def is_installed():
    """Best-effort check: PATH lookup first, then the usual install locations."""
    if shutil.which("tailscale"):
        return True
    return any(os.path.exists(path) for path in _KNOWN_INSTALL_PATHS)


def open_download_page():
    """Open Tailscale's own download page in the system browser. Never raises."""
    try:
        webbrowser.open(DOWNLOAD_URL)
        return True
    except OSError:
        return False
