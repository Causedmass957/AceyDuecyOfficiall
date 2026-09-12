# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build spec for Acey Duecy.

Build locally with:
    pyinstaller AceyDuecy.spec

Produces a --onedir build in dist/AceyDuecy/AceyDuecy.exe -- no Python
install required on the machine that runs it. This is the exact spec the
CI/CD pipeline (.github/workflows/dev-build.yml, release.yml) invokes, so a
local build and a pipeline build are identical.

VERSION (and CHANNEL, when the release pipeline writes one for a
dev/staging build) are bundled as plain data files, alongside assets/, so
Paths.resource_path() finds them both in dev and once frozen -- PyInstaller
sets sys._MEIPASS to this bundle's root at runtime.
"""
import os

block_cipher = None
APP_NAME = "AceyDuecy"

# CHANNEL is optional -- only present for a dev/staging build that a
# pipeline step wrote before invoking PyInstaller. A plain local/production
# build has no such file, which Paths.py treats as "no channel".
#
# assets/ is optional for the same reason it's conditional here: as of this
# pipeline landing, assets/splash.jpg is still someone else's uncommitted,
# in-progress work, not yet in the repo. main.py already loads the splash
# image inside a try/except and falls back to no splash, so building
# without assets/ present is safe -- once that work is committed, this
# picks it up automatically with no pipeline change needed.
datas = [("VERSION", ".")]
if os.path.isdir("assets"):
    datas.append(("assets", "assets"))
if os.path.exists("CHANNEL"):
    datas.append(("CHANNEL", "."))

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # pygame.pkgdata imports pkg_resources only inside a try/except ImportError,
    # falling back to safe stubs it never actually needs (this game uses
    # pygame.font.SysFont exclusively, never pygame's own bundled default
    # font/icon resources that pkgdata serves). Pulling pkg_resources in here
    # drags a broken setuptools/jaraco -> backports chain into the frozen
    # build (ModuleNotFoundError: No module named 'backports' at startup) --
    # excluding it lets pygame hit its own working fallback instead.
    excludes=["pkg_resources", "setuptools"],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # windowed -- no console flash behind the game
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)
