"""Task 5 — the anti-decorative test.

If breaking a claim's evidence changes nothing, Tasks 1–4 were decoration and
the spine is fiction. This is the only test in the suite whose purpose is to
attack the checker rather than exercise it.
"""

import stat
from pathlib import Path

from spine_check.cli import main

FIX = Path(__file__).parent / "fixtures"
REPO = FIX / "repo_tamper"


def _force_exec(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def test_baseline_repo_passes():
    assert main([str(REPO), "--claims", "--adrs"]) == 0, "baseline must pass first"


def test_tampering_with_a_claim_is_detected():
    script = REPO / "verify.sh"
    original = script.read_text()
    try:
        script.write_text("#!/bin/sh\nexit 1\n")
        _force_exec(script)
        assert main([str(REPO), "--claims", "--adrs"]) == 1, (
            "a broken claim must fail the checker"
        )
    finally:
        script.write_text(original)
        _force_exec(script)


def test_deleting_the_claim_is_detected():
    """Removing the manifest is not a way to make the repo compliant."""
    manifest = REPO / "spine.manifest.json"
    stash = manifest.with_suffix(".json.bak")
    try:
        manifest.rename(stash)
        assert main([str(REPO), "--claims", "--adrs"]) == 2, (
            "a repo with no manifest must be non-compliant, not vacuously compliant"
        )
    finally:
        stash.rename(manifest)


def test_spine_recovers_after_tamper_is_reverted():
    assert main([str(REPO), "--claims", "--adrs"]) == 0


def test_tampering_with_the_adrs_is_detected():
    adr = REPO / "docs" / "adr" / "0001-x.md"
    original = adr.read_text()
    try:
        stripped = "\n".join(
            line for line in original.splitlines() if not line.startswith("## Verification")
        )
        adr.write_text(stripped)
        assert main([str(REPO), "--claims", "--adrs"]) == 2, (
            "stripping the Verification section must be caught"
        )
    finally:
        adr.write_text(original)


def test_a_skipped_claim_cannot_satisfy_the_spine():
    """The classic 'green because it tested nothing' failure."""
    script = REPO / "verify.sh"
    original = script.read_text()
    try:
        script.write_text("#!/bin/sh\nexit 5\n")
        _force_exec(script)
        assert main([str(REPO), "--claims", "--adrs"]) == 0, "without --ci a skip is tolerated"
        assert main([str(REPO), "--claims", "--adrs", "--ci"]) == 1, (
            "under --ci, a skip that proves nothing must fail"
        )
    finally:
        script.write_text(original)
        _force_exec(script)