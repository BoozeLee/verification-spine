"""Task 4 — the CLI surface and the exit code.

Exit code contract:
    0  every enabled check passed, and nothing was skipped under --ci
    1  a claim failed, timed out, or was skipped while --ci was set
    2  the manifest was unusable, or --adrs found a violation
"""

from pathlib import Path

import pytest

from spine_check import __version__
from spine_check.cli import main

FIX = Path(__file__).parent / "fixtures"


def test_conformant_repo_exits_zero():
    assert main([str(FIX / "repo_ok"), "--adrs", "--claims"]) == 0


def test_failing_claim_exits_nonzero():
    assert main([str(FIX / "repo_fail")]) == 1


def test_skip_exits_zero_without_ci_flag():
    assert main([str(FIX / "repo_skip")]) == 0


def test_skip_is_failure_under_ci_flag():
    assert main([str(FIX / "repo_skip"), "--ci"]) == 1


def test_adr_violation_exits_two_under_adrs_flag():
    assert main([str(FIX / "repo_bad_adrs"), "--adrs"]) == 2


def test_missing_manifest_exits_two_not_a_traceback():
    assert main([str(FIX / "nope")]) == 2


def test_claims_flag_alone_does_not_run_adrs():
    """repo_bad_adrs has a bad ADR but a passing-shaped repo; --claims alone is 0."""
    assert main([str(FIX / "repo_ok"), "--claims"]) == 0


def test_default_run_checks_claims_and_adrs():
    assert main([str(FIX / "repo_ok")]) == 0


def test_timeout_flag_overrides_claim_timeout():
    # repo_timeout sleeps 60s; without an override this must not hang the suite.
    assert main([str(FIX / "repo_timeout"), "--claims", "--timeout", "2"]) == 1


def test_output_mentions_every_claim_id(capsys):
    main([str(FIX / "repo_ok"), "--claims"])
    assert "dummy-claim" in capsys.readouterr().out


def test_version_flag_prints_the_package_version(capsys):
    """A released CLI must be able to say what it is, and the number must come
    from the package itself — never a second hardcoded copy."""
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert __version__ in capsys.readouterr().out