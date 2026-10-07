"""B3 — does a claim's evidence actually prove the claim?

The spine's original weakness: a claim names a `verify` command, the command
exits 0, and the spine says PASS. But `true` exits 0. So the original spine
proved only that a command *ran* — it certified `echo hi` as proof of any
statement. A green checkmark on a false claim, which is the exact failure this
project exists to prevent.

Three layers, none sufficient alone:

  DENYLIST   reject verify commands that cannot fail by construction.
  MUTATION   if a claim declares `mutate`, the verdict must flip when its
             subject is deliberately broken. A claim that does not flip is
             **vacuous**: it would never notice its subject being false.
  STATE      report `verified` / `green` / `vacuous` / `unprovable` / `denied`
             / `broken` rather than a bare PASS, following the four states in
             the `proof-before-claim` discipline: a check that has only ever
             passed is *green*, not *verified*.

**The equivalent-mutant trap.** A `mutate` that breaks something semantically
irrelevant leaves `verify` correctly passing. A naive checker calls that claim
vacuous — a FALSE ACCUSATION, which is worse than a false green, because it
teaches people to ignore the tool. So the mutate-effect proof is mandatory:
before any vacuity verdict, the working tree must be shown to have actually
changed. A no-op mutate yields UNPROVABLE, never VACUOUS.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from spine_check.models import Claim
from spine_check.runner import ClaimOutcome, Outcome, run_verify

#: Commands that exit 0 without inspecting anything. Matching is on the resolved
#: argv[0] basename, so `/bin/true` and `true` are both caught while a real
#: `truthy-check` is not.
TRIVIAL_COMMANDS = frozenset({":", "true", "echo", "exit", "pass", "nop"})

#: Directories excluded from the tree fingerprint — bookkeeping, not subject.
_FINGERPRINT_SKIP = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}


class ClaimState(str, Enum):
    #: verify passed AND flipped when the subject was deliberately broken.
    VERIFIED = "verified"
    #: verify passed; no mutation was declared, so it has never been seen to fail.
    GREEN = "green"
    #: verify passed even after its declared mutate broke the subject.
    VACUOUS = "vacuous"
    #: a mutate was declared but changed nothing, so vacuity cannot be concluded.
    UNPROVABLE = "unprovable"
    #: the verify command cannot fail by construction.
    DENIED = "denied"
    #: verify did not pass to begin with.
    BROKEN = "broken"


@dataclass(frozen=True)
class VacuityResult:
    claim_id: str
    state: ClaimState
    reason: str
    flip_rate: str | None = None
    baseline: ClaimOutcome | None = None
    mutated: ClaimOutcome | None = None
    restored: bool = True

    @property
    def acceptable(self) -> bool:
        return self.state in (ClaimState.VERIFIED, ClaimState.GREEN)


def is_trivially_passing(command: str) -> bool:
    """True when `command` exits 0 without inspecting anything."""
    import shlex

    if not command.strip():
        return True
    try:
        argv = shlex.split(command)
    except ValueError:
        return True
    if not argv:
        return True
    try:
        basename = Path(argv[0]).name
    except (TypeError, ValueError):
        basename = argv[0]
    # `true --version` is still trivial; arguments do not make it meaningful.
    return basename in TRIVIAL_COMMANDS


def _iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if any(part in _FINGERPRINT_SKIP for part in path.relative_to(root).parts):
            continue
        yield path


def _iter_symlinks(root: Path) -> list[Path]:
    """Symlinks under `root`, excluded from the snapshot on purpose.

    A symlink's *target* is not the repository's content, and a mutation can
    plant one pointing anywhere. They are therefore never fingerprinted or
    snapshotted — and never written through during restore — only unlinked.
    """
    root = Path(root)
    return sorted(p for p in root.rglob("*") if p.is_symlink())


def tree_fingerprint(root: Path) -> str:
    """A stable hash of every non-bookkeeping file under `root`.

    Used as the mutate-effect precondition: if the fingerprint is unchanged
    after `mutate` ran, the mutation changed nothing and no vacuity verdict may
    be drawn from it.
    """
    digest = hashlib.sha256()
    for path in _iter_files(Path(root)):
        digest.update(str(path.relative_to(root)).encode("utf-8", "replace"))
        digest.update(b"\0")
        try:
            digest.update(path.read_bytes())
        except OSError:
            digest.update(b"<unreadable>")
        digest.update(b"\0")
    return digest.hexdigest()


def _restore(root: Path, mutate_argv: list[str], timeout: int) -> bool:
    """Best-effort restore. A destructive mutate is the author's error to declare."""
    try:
        from spine_check.runner import _as_text  # local import to avoid a cycle
    except ImportError:  # pragma: no cover
        _as_text = str  # type: ignore[assignment]

    import subprocess

    restore_argv = [a for a in mutate_argv if a not in ("--restore",)]
    if restore_argv == mutate_argv:
        return False
    try:
        proc = subprocess.run(
            restore_argv, cwd=root, capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def snapshot_tree(root: Path) -> dict[str, bytes]:
    """Capture every non-bookkeeping file's bytes so the tree can be put back.

    Mutation testing must not depend on the working copy being a clean git
    checkout. An earlier version restored with `git checkout -- .`, which
    silently does nothing for untracked files — so a mutation could outlive the
    run and quietly poison the next one. Snapshotting is self-contained and
    works in any repository, tracked or not.
    """
    root = Path(root)
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in _iter_files(root)
    }


def restore_tree(root: Path, snapshot: dict[str, bytes]) -> bool:
    """Put the tree back exactly as it was. Returns False if that failed.

    Files the mutation created are unlinked; directories it created are pruned
    bottom-up. Pruning matters because `tree_fingerprint` hashes files only, so
    an empty directory left behind is invisible to the restore check and would
    accumulate across runs as unremarked debris.
    """
    root = Path(root)
    try:
        # Symlinks first, and unconditionally: a mutation may have planted one
        # pointing at a file this restore is about to write. Unlinking before
        # any write is what stops the write going through the link.
        for link in _iter_symlinks(root):
            link.unlink()
        for rel in _iter_files(root):
            rel_str = str(rel.relative_to(root))
            if rel_str not in snapshot:
                rel.unlink()  # created by the mutation
        for rel_str, data in snapshot.items():
            dest = root / rel_str
            # A snapshot entry could itself be a path the mutation turned into
            # a symlink; unlink before writing so we never traverse one.
            if dest.is_symlink():
                dest.unlink()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        _prune_empty_dirs(root)
    except OSError:
        return False
    return tree_fingerprint(root) == tree_fingerprint_of(snapshot)


def _prune_empty_dirs(root: Path) -> None:
    """Remove empty directories under `root`, deepest first. Never removes `root`."""
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        d = Path(dirpath)
        if d == root:
            continue
        try:
            if not any(d.iterdir()):
                d.rmdir()
        except OSError:
            pass


def tree_fingerprint_of(snapshot: dict[str, bytes]) -> str:
    """The fingerprint a snapshot would produce if restored."""
    digest = hashlib.sha256()
    for rel in sorted(snapshot):
        digest.update(rel.encode("utf-8", "replace"))
        digest.update(b"\0")
        digest.update(snapshot[rel])
        digest.update(b"\0")
    return digest.hexdigest()


def check_claim_vacuity(claim: Claim, repo_root: Path) -> VacuityResult:
    """Classify a claim's evidence: does it prove anything, and could it notice?"""
    repo_root = Path(repo_root)

    if is_trivially_passing(claim.verify):
        return VacuityResult(
            claim.id,
            ClaimState.DENIED,
            f"verify command {claim.verify!r} cannot fail by construction",
        )

    baseline = run_verify(claim, repo_root)
    if not baseline.passed:
        return VacuityResult(
            claim.id,
            ClaimState.BROKEN,
            f"verify did not pass to begin with ({baseline.describe()})",
            baseline=baseline,
        )

    if not claim.mutate:
        return VacuityResult(
            claim.id,
            ClaimState.GREEN,
            "verify passed; no `mutate` declared, so it has never been seen to fail",
            baseline=baseline,
        )

    # --- mutation campaign -------------------------------------------------
    import shlex
    import subprocess

    try:
        mutate_argv = shlex.split(claim.mutate)
    except ValueError as exc:
        return VacuityResult(
            claim.id,
            ClaimState.UNPROVABLE,
            f"unparseable mutate command: {exc}",
            baseline=baseline,
        )

    before = tree_fingerprint(repo_root)
    snapshot = snapshot_tree(repo_root)

    try:
        mut = subprocess.run(
            mutate_argv, cwd=repo_root, capture_output=True, text=True, timeout=claim.timeout
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return VacuityResult(
            claim.id,
            ClaimState.UNPROVABLE,
            f"mutate command could not run: {exc}",
            baseline=baseline,
        )

    if mut.returncode != 0:
        return VacuityResult(
            claim.id,
            ClaimState.UNPROVABLE,
            f"mutate exited {mut.returncode}; a vacuity verdict needs a working mutation",
            baseline=baseline,
        )

    after = tree_fingerprint(repo_root)
    flipped_evidence: ClaimOutcome | None = None

    if after == before:
        # Equivalent-mutant guard. `mutate` ran and succeeded but changed
        # nothing, so nothing was actually perturbed. Saying "vacuous" here
        # would be an accusation we cannot support.
        state, reason = (
            ClaimState.UNPROVABLE,
            "mutate ran but changed nothing in the working tree; vacuity cannot be concluded",
        )
        flip_rate = "0/1"
    else:
        flipped_evidence = run_verify(claim, repo_root)
        flip_rate = "1/1" if not flipped_evidence.passed else "0/1"
        if flipped_evidence.passed:
            state, reason = (
                ClaimState.VACUOUS,
                "verify still passed after mutate broke the subject — the evidence is "
                "not coupled to the claim",
            )
        else:
            state, reason = (
                ClaimState.VERIFIED,
                "verify flipped to failure when the subject was deliberately broken",
            )

    # --- restore ----------------------------------------------------------
    # Snapshot-based, not git-based: see snapshot_tree(). A declared `--restore`
    # script runs first (the author's own undo), then the snapshot guarantees
    # the tree is byte-identical to how we found it.
    restored_ok = True
    if "--restore" in claim.mutate:
        restored_ok = _restore(repo_root, mutate_argv, claim.timeout)
    if not restore_tree(repo_root, snapshot):
        restored_ok = False

    return VacuityResult(
        claim.id,
        state,
        reason,
        flip_rate=flip_rate,
        baseline=baseline,
        mutated=flipped_evidence,
        restored=restored_ok,
    )