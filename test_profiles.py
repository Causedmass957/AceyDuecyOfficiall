"""ProfileManager create/read round-trip, against a throwaway db file.

Uses an explicit db_path (tmp_path fixture) rather than the default so this
never touches the real %APPDATA%\\AceyDuecy stats.db, even outside the
conftest.py channel isolation.
"""
from ProfileManager import ProfileManager


def test_create_and_read_profile(tmp_path):
    pm = ProfileManager(db_path=str(tmp_path / "stats.db"))

    pm.create_profile("Arnie")

    assert "Arnie" in pm.get_all_profiles()
    profile = pm.get_profile("Arnie")
    assert profile is not None
    assert profile["games_played"] == 0
    assert profile["wins"] == 0


def test_unknown_profile_returns_none(tmp_path):
    pm = ProfileManager(db_path=str(tmp_path / "stats.db"))

    assert pm.get_profile("NobodyHome") is None
