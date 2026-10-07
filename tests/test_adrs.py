"""Task 3 — ADR enforcement (rule R3).

Rule R3: every binding decision names its enforcement. An ADR without a
`## Verification` section is documentation, not a constraint.

Review Focus cases pinned here:
  - a superseded ADR must be exempt (history is not rewritten)
  - a claim citing an ADR that does not exist must be a hard error
"""

from pathlib import Path

from spine_check.adrs import check_adrs
from spine_check.models import load_manifest

FIX = Path(__file__).parent / "fixtures"


def test_conformant_repo_has_no_violations():
    assert check_adrs(FIX / "repo_ok", load_manifest(FIX / "repo_ok")) == []


def test_adr_without_verification_section_is_a_violation():
    v = check_adrs(FIX / "repo_bad_adrs", load_manifest(FIX / "repo_ok"))
    assert any("Verification" in x.reason for x in v)


def test_superseded_adr_is_exempt():
    assert check_adrs(FIX / "repo_superseded", load_manifest(FIX / "repo_ok")) == []


def test_dangling_adr_reference_is_a_violation():
    v = check_adrs(FIX / "repo_dangling_adr", load_manifest(FIX / "repo_dangling_adr"))
    assert v, "a claim bound to a nonexistent ADR must be reported"
    assert any("9999" in x.reason for x in v)


def test_repo_with_no_adr_directory_is_not_a_violation():
    """R3 binds decisions that exist; it does not demand an ADR exists."""
    assert check_adrs(FIX / "repo_skip", load_manifest(FIX / "repo_ok")) == []


def test_verification_section_with_only_a_placeholder_is_a_violation():
    v = check_adrs(FIX / "repo_placeholder_adr", load_manifest(FIX / "repo_ok"))
    assert any("Verification" in x.reason for x in v)

def test_both_adr_filename_conventions_are_recognised():
    """agentic-setup globs ADR-*.md; this repo produced 0001-*.md. Both count."""
    from spine_check.adrs import _existing_adr_ids

    ids = _existing_adr_ids(FIX / "repo_mixed_adr" / "docs" / "adr")
    assert "0001" in ids and "0002" in ids, ids
