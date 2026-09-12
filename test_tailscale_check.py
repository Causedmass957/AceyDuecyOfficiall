"""Unit tests for TailscaleCheck.py. No real Tailscale install required --
shutil.which and os.path.exists are monkeypatched.
"""
import TailscaleCheck


def test_detected_via_path(monkeypatch):
    monkeypatch.setattr(TailscaleCheck.shutil, "which", lambda name: r"C:\tools\tailscale.exe")
    assert TailscaleCheck.is_installed() is True


def test_detected_via_known_install_path(monkeypatch):
    monkeypatch.setattr(TailscaleCheck.shutil, "which", lambda name: None)
    monkeypatch.setattr(
        TailscaleCheck.os.path, "exists",
        lambda p: p == TailscaleCheck._KNOWN_INSTALL_PATHS[0],
    )
    assert TailscaleCheck.is_installed() is True


def test_not_detected(monkeypatch):
    monkeypatch.setattr(TailscaleCheck.shutil, "which", lambda name: None)
    monkeypatch.setattr(TailscaleCheck.os.path, "exists", lambda p: False)
    assert TailscaleCheck.is_installed() is False


def test_open_download_page_never_raises(monkeypatch):
    monkeypatch.setattr(TailscaleCheck.webbrowser, "open", lambda url: (_ for _ in ()).throw(OSError("no browser")))
    assert TailscaleCheck.open_download_page() is False
