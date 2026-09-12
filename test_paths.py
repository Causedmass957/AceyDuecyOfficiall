"""Unit tests for Paths.py: resource_path()/data_dir()/migrate_legacy_file().

Every test redirects APPDATA and _SOURCE_DIR into tmp_path via monkeypatch so
nothing here ever touches the real %APPDATA%\\AceyDuecy or the repo itself.
"""
import sys

import Paths


def test_resource_path_uses_source_dir_when_not_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(Paths, "_SOURCE_DIR", str(tmp_path))
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    assert Paths.resource_path("assets", "splash.jpg") == str(tmp_path / "assets" / "splash.jpg")


def test_resource_path_uses_meipass_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert Paths.resource_path("assets", "splash.jpg") == str(tmp_path / "assets" / "splash.jpg")


def test_data_dir_created_under_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setattr(Paths, "APP_CHANNEL", "")
    d = Paths.data_dir()
    assert d == str(tmp_path / "AceyDuecy")
    assert (tmp_path / "AceyDuecy").is_dir()


def test_data_dir_namespaced_by_channel(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setattr(Paths, "APP_CHANNEL", "beta")
    d = Paths.data_dir()
    assert d == str(tmp_path / "AceyDuecy" / "beta")


def test_migrate_moves_existing_legacy_file(monkeypatch, tmp_path):
    appdata = tmp_path / "appdata"
    source = tmp_path / "source"
    appdata.mkdir()
    source.mkdir()
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setattr(Paths, "APP_CHANNEL", "")
    monkeypatch.setattr(Paths, "_SOURCE_DIR", str(source))

    legacy_file = source / "settings.json"
    legacy_file.write_text('{"fullscreen": true}')

    new_path = Paths.migrate_legacy_file("settings.json")

    assert new_path == str(appdata / "AceyDuecy" / "settings.json")
    assert not legacy_file.exists()
    assert (appdata / "AceyDuecy" / "settings.json").read_text() == '{"fullscreen": true}'


def test_migrate_is_a_noop_once_new_file_exists(monkeypatch, tmp_path):
    appdata = tmp_path / "appdata"
    source = tmp_path / "source"
    appdata.mkdir()
    source.mkdir()
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setattr(Paths, "APP_CHANNEL", "")
    monkeypatch.setattr(Paths, "_SOURCE_DIR", str(source))

    (appdata / "AceyDuecy").mkdir()
    (appdata / "AceyDuecy" / "settings.json").write_text("real")
    (source / "settings.json").write_text("stale leftover")

    new_path = Paths.migrate_legacy_file("settings.json")

    assert (source / "settings.json").exists()  # untouched, not overwritten
    assert open(new_path).read() == "real"


def test_migrate_is_a_noop_when_nothing_exists(monkeypatch, tmp_path):
    appdata = tmp_path / "appdata"
    source = tmp_path / "source"
    appdata.mkdir()
    source.mkdir()
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setattr(Paths, "APP_CHANNEL", "")
    monkeypatch.setattr(Paths, "_SOURCE_DIR", str(source))

    new_path = Paths.migrate_legacy_file("savegame.json")

    assert not (appdata / "AceyDuecy" / "savegame.json").exists()
    assert new_path == str(appdata / "AceyDuecy" / "savegame.json")
