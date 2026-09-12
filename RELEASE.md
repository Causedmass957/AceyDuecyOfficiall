# Release pipeline

Three environments, one branch (`main`), promoted by tags rather than
long-lived branches -- see `.github/workflows/`.

| Environment | Trigger | Output | Audience |
|---|---|---|---|
| **Dev** | every push to `main` | `AceyDuecy-dev.zip` (onedir, no installer) as a 14-day GitHub Actions artifact | you |
| **Staging** | tag `v*-beta*` or `v*-rc*` | full installer, GitHub **pre-release** | playtesters |
| **Production** | a clean tag `vX.Y.Z` | full installer, GitHub **latest release** | everyone |

## Cutting a release

```bash
# Staging / beta build, for testers:
git tag v0.6.0-beta1
git push origin v0.6.0-beta1

# Production build, once it's actually ready:
git tag v1.0.0
git push origin v1.0.0
```

That's it — `.github/workflows/release.yml` picks up the tag, runs the full
test suite, builds `AceyDuecy.exe` with PyInstaller, wraps it with Inno
Setup into `AceyDuecySetup-<version>.exe`, and publishes it as a GitHub
Release (marked pre-release for a `-beta`/`-rc` tag, latest otherwise).
Nothing is published if the tests fail.

Bump the version in [`VERSION`](VERSION) as part of the commit you're about
to tag -- the tag is what drives the *build*, but `VERSION` is what
`UpdateChecker.py` compares against once it's running, so they should agree.

## One-time setup still needed on GitHub (not doable from a workflow file)

To make the `staging`/`production` gate in `release.yml` actually pause for
approval instead of publishing the instant a tag is pushed: go to this
repo's **Settings -> Environments**, open `staging` and `production`, and
add yourself as a required reviewer under "Deployment protection rules".
Until that's set, both environments exist but don't block anything.

## Local build (same steps the pipeline runs)

```bash
pip install -r requirements-dev.txt
python -m pytest -m "not manual" -v
pyinstaller AceyDuecy.spec
# installer.iss needs Inno Setup (https://jrsoftware.org/isinfo.php) installed locally:
iscc installer.iss /DMyAppVersion=0.1.0
```

Output: `dist/AceyDuecy/AceyDuecy.exe` (raw onedir build) and
`installer_output/AceyDuecySetup-0.1.0.exe` (the thing you actually hand
someone).

## Save data across environments

`Paths.py` keeps dev/staging/production save data separate on the same
machine (`%APPDATA%\AceyDuecy`, `%APPDATA%\AceyDuecy\dev`,
`%APPDATA%\AceyDuecy\beta`) via a `CHANNEL` file the pipeline stamps in
before building. A production build has no `CHANNEL` file and uses the
plain folder. This is also why it's safe to install a beta build and the
real release side by side to test an upgrade.

## What CI actually gates

`.github/workflows/ci.yml` runs on every push/PR and is the one thing every
other workflow depends on passing: `pytest -m "not manual"`. The `manual`
marker (`test_lan.py`) needs a real NIC/firewall to mean anything, so it's
never run in CI -- run it by hand (`python test_lan.py`) before a release
that touches networking.

## In-game update notice + Tailscale prompt

`UpdateChecker.py` checks GitHub's latest release once at startup (off the
main thread, never blocks) and shows a small "update available" banner on
the main menu if this build is behind. `TailscaleCheck.py` detects whether
Tailscale is installed and, if not, shows a banner on the host/join lobby
screens with a one-key (`T`) link to Tailscale's own download page --
neither of these bundles or installs anything on the player's behalf.
