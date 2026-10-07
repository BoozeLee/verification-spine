"""B3: a claim's verify command ran, or did it prove the claim?

Three independent detectors, because no single one is sufficient:

  1. DENYLIST  — reject verify commands that cannot fail by construction
                 (`true`, `:`, `echo`, `exit 0`, `pass`). Catches the degenerate
                 case statically, with no mutation machinery.
  2. MUTATION  — a claim may declare `mutate`, a command that deliberately breaks
                 the thing the claim is about. If verify still passes afterwards,
                 the claim would never notice its own subject being false.
  3. STATE     — report `verified` / `green` / `vacuous` rather than a bare PASS.
                 Following the proof-before-claim discipline: a check that has
                 only ever passed is *green*, not *verified*.

The research surfaced the trap that makes naive mutation testing wrong, so it is
pinned here: equivalent mutants. A `mutate` that breaks something semantically
irrelevant leaves `verify` correctly passing, and a naive checker calls that claim
vacuous — a FALSE ACCUSATION, which is worse than a false green. Therefore the
mutate-effect proof is mandatory before any vacuity verdict.
"""

import stat
from pathlib import Path

import pytest

from spine_check.models import load_manifest
from spine_check.runner import run_verify
from spine_check.vacuity import (
    ClaimState,
    check_claim_vacuity,
    is_trivially_passing,
    tree_fingerprint,
)

FIX = Path(__file__).parent / "fixtures"


# --- 1. denylist ---------------------------------------------------------------

@pytest.mark.parametrize(
    "cmd",
    ["true", "/bin/true", ":", "exit 0", "echo", "echo hi", "pass",
     "/usr/bin/true", "echo anything", "true --version", "nop"],
)
def test_trivially_passing_commands_are_rejected(cmd):
    assert is_trivially_passing(cmd) is True, f"{cmd!r} cannot fail by construction"


@pytest.mark.parametrize(
    "cmd",
    ["./verify.sh", "python3 -m pytest -q", "cargo test", "./bin/self-check.sh",
     "truthy-check", "echo-helper", "trueish"],
)
def test_real_commands_are_not_rejected(cmd):
    assert is_trivially_passing(cmd) is False


def test_empty_command_is_trivially_passing():
    assert is_trivially_passing("") is True
    assert is_trivially_passing("   ") is True


# --- 2. tree fingerprint (the mutate-effect precondition) -----------------------

def test_fingerprint_changes_when_a_file_changes(tmp_path):
    f = tmp_path / "subject.py"
    f.write_text("ORIGINAL = 1\n")
    before = tree_fingerprint(tmp_path)
    f.write_text("BROKEN = 999\n")
    assert tree_fingerprint(tmp_path) != before


def test_fingerprint_is_stable_when_nothing_changes(tmp_path):
    (tmp_path / "a.txt").write_text("same\n")
    assert tree_fingerprint(tmp_path) == tree_fingerprint(tmp_path)


def test_fingerprint_ignores_the_git_directory(tmp_path):
    (tmp_path / "a.txt").write_text("same\n")
    before = tree_fingerprint(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    assert tree_fingerprint(tmp_path) == before


# --- 3. mutation: does verify actually flip? -----------------------------------

def test_a_mutant_that_flips_verify_yields_verified():
    repo = FIX / "repo_mutant_flip"
    claim = load_manifest(repo).claims[0]
    result = check_claim_vacuity(claim, repo)
    assert result.state is ClaimState.VERIFIED, result.reason
    assert result.flip_rate == "1/1"


def test_a_mutant_that_does_not_flip_verify_yields_vacuous():
    """The core of B3: a claim that cannot notice its subject being false."""
    repo = FIX / "repo_mutant_vacuous"
    claim = load_manifest(repo).claims[0]
    result = check_claim_vacuity(claim, repo)
    assert result.state is ClaimState.VACUOUS, result.reason
    assert result.flip_rate == "0/1"


def test_a_mutant_that_changes_nothing_is_unprovable_not_vacuous():
    """Equivalent-mutant guard: a no-op mutate cannot accuse the claim."""
    repo = FIX / "repo_mutant_noop"
    claim = load_manifest(repo).claims[0]
    result = check_claim_vacuity(claim, repo)
    assert result.state is ClaimState.UNPROVABLE, result.reason
    assert result.flip_rate == "0/1"


def test_a_claim_with_no_mutate_is_green_not_verified():
    repo = FIX / "repo_ok"
    claim = load_manifest(repo).claims[0]
    result = check_claim_vacuity(claim, repo)
    assert result.state is ClaimState.GREEN, result.reason
    assert result.flip_rate is None


def test_mutation_restores_the_working_tree():
    repo = FIX / "repo_mutant_flip"
    before = tree_fingerprint(repo)
    claim = load_manifest(repo).claims[0]
    check_claim_vacuity(claim, repo)
    assert tree_fingerprint(repo) == before, "mutation must not leave the tree dirty"


def test_mutation_restores_even_when_the_claim_is_vacuous():
    repo = FIX / "repo_mutant_vacuous"
    before = tree_fingerprint(repo)
    claim = load_manifest(repo).claims[0]
    check_claim_vacuity(claim, repo)
    assert tree_fingerprint(repo) == before


def test_a_failing_verify_is_a_failure_not_a_state_verdict():
    """A claim that does not pass to begin with is simply broken."""
    repo = FIX / "repo_fail"
    claim = load_manifest(repo).claims[0]
    result = check_claim_vacuity(claim, repo)
    assert result.state is ClaimState.BROKEN, result.reason


def test_denied_command_short_circuits_before_running_anything():
    repo = FIX / "repo_ok"
    from spine_check.models import Claim

    claim = Claim(id="trivial", statement="s", verify="true", expect="exit 0", timeout=10)
    result = check_claim_vacuity(claim, repo)
    assert result.state is ClaimState.DENIED, result.reason

def test_mutation_that_creates_directories_leaves_nothing_behind(tmp_path):
    """BUG 5: restore cleaned files but left empty directory shells.

    tree_fingerprint hashes files only, so a leftover empty directory is
    invisible to it — the tree looked restored while carrying debris that
    accumulates across runs.
    """
    from spine_check.vacuity import restore_tree, snapshot_tree

    (tmp_path / "keep.py").write_text("x = 1\n")
    snapshot = snapshot_tree(tmp_path)

    (tmp_path / "created" / "deep").mkdir(parents=True)
    (tmp_path / "created" / "deep" / "f.txt").write_text("new\n")

    assert restore_tree(tmp_path, snapshot) is True
    assert not (tmp_path / "created").exists(), "empty directory shells survived restore"


def test_mutation_that_deletes_a_file_restores_it(tmp_path):
    from spine_check.vacuity import restore_tree, snapshot_tree

    subject = tmp_path / "subject.py"
    subject.write_text('SUBJECT = "intact"\n')
    snapshot = snapshot_tree(tmp_path)

    subject.unlink()
    assert restore_tree(tmp_path, snapshot) is True
    assert subject.read_text() == 'SUBJECT = "intact"\n'
