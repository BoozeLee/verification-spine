"""Task 2 — the verify runner (rule R2).

Review Focus cases pinned here:
  - a command that hangs forever must be TIMEOUT, never PASS
  - exit code 5 must be SKIP, never PASS
"""

import os
import stat

import pytest
from pathlib import Path

from spine_check.models import Claim
from spine_check.runner import ClaimOutcome, Outcome, run_verify

FIX = Path(__file__).parent / "fixtures"


def _claim(verify="./verify.sh", timeout=300):
    return Claim(
        id="c", statement="s", verify=verify, expect="exit 0", timeout=timeout
    )


def _make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def test_passing_command_is_pass():
    r = run_verify(_claim(), FIX / "repo_ok")
    assert r.outcome is Outcome.PASS
    assert r.exit_code == 0


def test_exit_5_is_skip_not_pass():
    r = run_verify(_claim(), FIX / "repo_skip")
    assert r.outcome is Outcome.SKIP
    assert r.exit_code == 5


def test_hanging_command_is_timeout_not_pass():
    r = run_verify(_claim(timeout=2), FIX / "repo_timeout")
    assert r.outcome is Outcome.TIMEOUT
    assert r.exit_code is None


def test_failing_command_is_fail():
    r = run_verify(_claim(verify="false"), FIX / "repo_ok")
    assert r.outcome is Outcome.FAIL
    assert r.exit_code == 1


def test_missing_binary_is_fail_not_an_escaping_exception():
    r = run_verify(_claim(verify="definitely-not-a-real-binary-xyz"), FIX / "repo_ok")
    assert r.outcome is Outcome.FAIL


def test_non_executable_verify_script_is_fail(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    script = repo / "verify.sh"
    script.write_text("#!/bin/sh\nexit 0\n")
    script.chmod(0o644)  # deliberately not executable
    r = run_verify(_claim(), repo)
    assert r.outcome is Outcome.FAIL


def test_command_runs_with_repo_root_as_cwd():
    r = run_verify(_claim(verify="pwd"), FIX / "repo_ok")
    assert r.outcome is Outcome.PASS
    assert os.path.realpath(r.stdout.strip()) == os.path.realpath(FIX / "repo_ok")


def test_output_is_captured_and_truncated():
    r = run_verify(_claim(verify="./noisy.sh"), FIX / "repo_ok")
    assert r.outcome is Outcome.PASS
    # The command emitted 9001 characters. The retained payload is capped at
    # MAX_CAPTURE and a marker is appended, so the total may exceed the cap.
    assert len(r.stdout) < 9001
    assert "truncated" in r.stdout
    assert len(r.stdout.split("\n… truncated")[0]) == 4000

@pytest.mark.parametrize(
    "cmd",
    [
        "./verify.sh && false",   # would FAIL in a shell
        "./verify.sh; false",     # would FAIL in a shell
        "./verify.sh || true",    # would PASS in a shell for the wrong reason
        "echo $(false)",          # command substitution
        "echo `false`",           # backtick substitution
    ],
)
def test_shell_metacharacters_never_pass_silently(cmd):
    """A `verify` string is argv, not shell text.

    Found by test_output_is_captured_and_truncated originally: `shlex.split`
    turns "./verify.sh && false" into ["./verify.sh", "&&", "false"], the script
    ignores its arguments and exits 0, and a claim that fails in any real shell
    was reported PASS. Every shell construct is now rejected outright.
    """
    r = run_verify(_claim(verify=cmd), FIX / "repo_ok")
    assert r.outcome is not Outcome.PASS, f"{cmd!r} must not silently pass"
    assert "shell composition" in r.stderr


def test_noisy_hang_is_timeout_not_a_crash():
    """B1: a command that floods stdout and then hangs must TIMEOUT, not raise.

    `subprocess.TimeoutExpired` carries its output as **bytes** even when the
    subprocess was opened with text=True — CPython stores the raw buffer before
    decoding. Feeding those bytes straight into the str-based truncation helper
    raised `TypeError: can't concat str to bytes`.

    A crash here is worse than a false pass: in CI it looks like a flake that
    someone re-runs, rather than a claim that failed.
    """
    r = run_verify(Claim(id="noisy-hang", statement="s", verify="./verify.sh",
                         expect="exit 0", timeout=3), FIX / "repo_noisy_hang")
    assert r.outcome is Outcome.TIMEOUT
    assert r.exit_code is None
    assert isinstance(r.stdout, str)


def test_run_verify_never_raises_for_odd_commands():
    """Every malformed or hostile command must come back as an outcome."""
    repo = FIX / "repo_ok"
    for cmd in ["", "   ", "nonexistent-binary-xyz", "/", "true", "'unbalanced",
                "--", "./verify.sh && false", "$(echo hi)", "a" * 500]:
        r = run_verify(_claim(verify=cmd, timeout=5), repo)
        assert isinstance(r, ClaimOutcome), f"{cmd!r} produced no outcome"
        assert isinstance(r.stdout, str) and isinstance(r.stderr, str)
