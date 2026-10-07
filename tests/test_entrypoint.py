"""B2: the installed entry point must actually run.

The first version of bin/spine-check never set PYTHONPATH, so `./bin/spine-check .`
died with "No module named spine_check". Every other test in this repo passed
while the command a user would actually type was broken — because they all
imported the package directly rather than going through the shim.

These tests deliberately run the shim against a FIXTURE repo, never against this
repository. The spine's own manifest claim runs the test suite, so pointing this
test at the spine repo recurses: shim -> spine-check -> self-check.sh -> pytest
-> this test -> shim -> ...
"""

import os
import stat
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SHIM = REPO / "bin" / "spine-check"
FIXTURE = Path(__file__).parent / "fixtures" / "repo_ok"

_CLEAN_ENV = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}


def _run(*args, cwd=REPO, env=None):
    return subprocess.run(
        [str(SHIM), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )


def test_shim_exists_and_is_executable():
    assert SHIM.is_file()
    assert SHIM.stat().st_mode & stat.S_IXUSR, "bin/spine-check must be executable"


def test_shim_runs_with_no_pythonpath_in_the_environment():
    assert "PYTHONPATH" not in _CLEAN_ENV
    r = _run(str(FIXTURE), "--claims", "--adrs", "--ci", env=_CLEAN_ENV)
    assert r.returncode == 0, f"stdout={r.stdout!r} stderr={r.stderr!r}"
    assert "dummy-claim" in r.stdout


def test_shim_locates_the_package_from_an_unrelated_cwd():
    """The shim must resolve its own path, not depend on the caller's cwd."""
    r = _run(str(FIXTURE), "--claims", cwd="/tmp", env=_CLEAN_ENV)
    assert r.returncode == 0, f"stderr={r.stderr!r}"


def test_shim_reports_a_missing_manifest_rather_than_tracing_back():
    r = _run(str(REPO / "tests" / "fixtures" / "nope"), "--claims", env=_CLEAN_ENV)
    assert r.returncode == 2
    assert "Traceback" not in r.stderr


def test_module_entry_point_also_works():
    r = subprocess.run(
        [sys.executable, "-m", "spine_check", str(FIXTURE), "--claims"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PYTHONPATH": str(REPO / "src")},
    )
    assert r.returncode == 0, f"stderr={r.stderr!r}"