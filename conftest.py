"""Pytest-wide setup, applied before any test module imports pygame or Paths.

Two things every test in this suite needs, regardless of which file it's in:

1. A headless SDL driver -- CI runners (and most dev machines running tests
   in the background) have no display/audio device. Without this,
   pygame.init() hangs or errors on any test that touches pygame at all
   (test_multiplayer_flow.py, test_lobby_ui.py, test_lan.py all do).

2. An isolated data channel -- ProfileManager/Settings/SaveManager default to
   Paths.data_dir(), which is the REAL %APPDATA%\\AceyDuecy the developer
   actually plays with. Without this, running the suite would create/modify
   real profiles and stats. ACEYDUECY_CHANNEL routes them into their own
   %APPDATA%\\AceyDuecy\\pytest sub-folder instead (see Paths.py).

setdefault() so a test that needs something different (test_lan.py sets its
own channel to test real LAN/firewall behaviour) can still override it.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("ACEYDUECY_CHANNEL", "pytest")
