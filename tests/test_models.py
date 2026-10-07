"""Task 1 — manifest parsing and static validation (rule R1)."""

from pathlib import Path

import pytest

from spine_check.models import ManifestError, load_manifest

FIX = Path(__file__).parent / "fixtures"


def test_loads_conformant_manifest():
    m = load_manifest(FIX / "repo_ok")
    assert m.project == "fixture-repo"
    assert m.spine_version == 1
    assert [c.id for c in m.claims] == ["dummy-claim"]


def test_claim_defaults_are_applied():
    m = load_manifest(FIX / "repo_ok")
    c = m.claims[0]
    assert c.timeout == 300
    assert c.evidence is None
    assert c.adrs == []


def test_duplicate_claim_id_is_hard_error():
    with pytest.raises(ManifestError) as e:
        load_manifest(FIX / "repo_dup_id")
    assert "duplicate" in str(e.value).lower()
    assert "dummy-claim" in str(e.value)


def test_missing_manifest_is_a_manifest_error_not_a_traceback():
    with pytest.raises(ManifestError):
        load_manifest(FIX / "does_not_exist")


def test_malformed_json_is_a_manifest_error():
    with pytest.raises(ManifestError):
        load_manifest(FIX / "repo_broken_json")