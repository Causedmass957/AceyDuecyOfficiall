"""Unit tests for UpdateChecker.py. No real network calls -- urlopen is
monkeypatched so this is fast and deterministic in CI.
"""
import io
import json

import UpdateChecker


def test_parse_plain_version():
    assert UpdateChecker._parse("1.2.3") == (1, 2, 3)


def test_parse_v_prefix_and_prerelease_suffix():
    assert UpdateChecker._parse("v0.6.0-beta1") == (0, 6, 0)


def test_parse_short_version_pads_with_zero():
    assert UpdateChecker._parse("v2") == (2, 0, 0)


def test_current_version_reads_bundled_file(monkeypatch, tmp_path):
    version_file = tmp_path / "VERSION"
    version_file.write_text("1.4.0\n")
    monkeypatch.setattr(UpdateChecker, "resource_path", lambda name: str(version_file))
    assert UpdateChecker.current_version() == "1.4.0"


def test_current_version_falls_back_when_missing(monkeypatch):
    monkeypatch.setattr(UpdateChecker, "resource_path", lambda name: "no/such/file")
    assert UpdateChecker.current_version() == "0.0.0"


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _fake_urlopen(payload):
    def _open(request, timeout=None):
        return _FakeResponse(json.dumps(payload).encode("utf-8"))
    return _open


def test_check_for_update_returns_newer_release(monkeypatch):
    monkeypatch.setattr(UpdateChecker, "current_version", lambda: "1.0.0")
    monkeypatch.setattr(
        UpdateChecker.urllib.request, "urlopen",
        _fake_urlopen({"tag_name": "v1.1.0", "html_url": "https://example.test/v1.1.0"}),
    )
    result = UpdateChecker.check_for_update()
    assert result == ("v1.1.0", "https://example.test/v1.1.0")


def test_check_for_update_returns_none_when_current(monkeypatch):
    monkeypatch.setattr(UpdateChecker, "current_version", lambda: "1.1.0")
    monkeypatch.setattr(
        UpdateChecker.urllib.request, "urlopen",
        _fake_urlopen({"tag_name": "v1.1.0", "html_url": "https://example.test/v1.1.0"}),
    )
    assert UpdateChecker.check_for_update() is None


def test_check_for_update_never_raises_on_network_failure(monkeypatch):
    def _boom(request, timeout=None):
        raise OSError("network unreachable")

    monkeypatch.setattr(UpdateChecker.urllib.request, "urlopen", _boom)
    assert UpdateChecker.check_for_update() is None
