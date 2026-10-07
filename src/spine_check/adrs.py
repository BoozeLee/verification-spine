"""Enforcing rule R3: every binding decision names its enforcement.

Owns: reading `docs/adr/*.md` and deciding whether each file constrains anything.

The rule is lifted from the global AGENTS.md — "an ADR without a `## Verification`
section naming its enforcement is documentation, not a constraint." This module is
that sentence made executable.

Two deliberate exemptions:
  - superseded ADRs. History is not rewritten when a decision changes.
  - repositories with no `docs/adr/` at all. R3 constrains decisions that exist;
    it does not manufacture them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from spine_check.models import Manifest

ADR_DIR = Path("docs") / "adr"

#: `## Verification`, any capitalisation, trailing whitespace tolerated.
_HEADING = re.compile(r"^##\s+verification\b", re.IGNORECASE)

#: Any `## ` heading — used to find where the Verification section ends.
_ANY_HEADING = re.compile(r"^##\s+")

#: A Status bullet declaring supersession. Emphasis markers are stripped before
#: matching, because the house style writes `- **Status:** superseded by …`,
#: putting the colon *inside* the bold run.
_SUPERSEDED = re.compile(r"^status\s*:\s*superseded", re.IGNORECASE)

_EMPHASIS = re.compile(r"[*_`]")

#: Text that is scaffolding rather than a real enforcement statement.
_PLACEHOLDER = re.compile(r"^<[^>]*>$|^tbd$|^todo$|\.\.\.$", re.IGNORECASE)


@dataclass(frozen=True)
class AdrViolation:
    path: str
    reason: str

    def __str__(self) -> str:
        return f"{self.path}: {self.reason}"


def _is_placeholder(line: str) -> bool:
    stripped = line.strip()
    return not stripped or _PLACEHOLDER.match(stripped) is not None


def _has_verification_heading(lines: list[str]) -> bool:
    return any(_HEADING.match(ln) for ln in lines)


def _is_superseded(lines: list[str]) -> bool:
    for line in lines:
        # Drop bullets, then emphasis, then leading whitespace, so
        # `- **Status:** superseded by ADR-0031` reduces to `Status: superseded …`.
        normalized = _EMPHASIS.sub("", line).strip()
        normalized = re.sub(r"^[-*+]\s*", "", normalized).strip()
        if _SUPERSEDED.match(normalized):
            return True
    return False


def _verification_body(text: str) -> list[str]:
    """Return the non-scaffolding lines under `## Verification`, if it exists."""
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if _HEADING.match(ln)), None)
    if start is None:
        return []

    body: list[str] = []
    for line in lines[start + 1 :]:
        if _ANY_HEADING.match(line):
            break
        if not _is_placeholder(line):
            body.append(line.strip())
    return body


def _existing_adr_ids(adr_dir: Path) -> set[str]:
    """Numeric ids (`0001`) of every ADR file present.

    Accepts both naming conventions in use on this machine:
      docs/adr/0001-slug.md      — what this repo produced
      docs/adr/ADR-0001-slug.md  — what agentic-setup/session-close.sh globs

    They disagreed until 2026-10-07: the gate required `ADR-*.md` while this
    module matched only leading digits, so an ADR the gate recognised was
    invisible here and any claim referencing it read as dangling.
    """
    ids: set[str] = set()
    if not adr_dir.is_dir():
        return ids
    for md in sorted(adr_dir.glob("*.md")):
        match = re.match(r"^(?:ADR-)?(\d+)", md.stem, re.IGNORECASE)
        if match:
            ids.add(match.group(1))
    return ids


def check_adrs(repo_root: Path, manifest: Manifest) -> list[AdrViolation]:
    """Every R3 violation in `repo_root`. Empty list means compliant.

    Checks two independent things:
      1. each ADR on disk names its enforcement, unless superseded
      2. each ADR id a claim refers to actually exists on disk
    """
    repo_root = Path(repo_root)
    adr_dir = repo_root / ADR_DIR
    violations: list[AdrViolation] = []

    if adr_dir.is_dir():
        for md in sorted(adr_dir.glob("*.md")):
            text = md.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            rel = str(md.relative_to(repo_root))

            if _is_superseded(lines):
                continue

            if not _has_verification_heading(lines):
                violations.append(
                    AdrViolation(rel, "no '## Verification' section — documentation, not a constraint")
                )
                continue

            if not _verification_body(text):
                violations.append(
                    AdrViolation(
                        rel,
                        "'## Verification' is present but names no enforcement",
                    )
                )

    on_disk = _existing_adr_ids(adr_dir)
    # Compare zero-stripped ids so a manifest may write "1", "0001" or "1-x"
    # and still bind to docs/adr/0001-x.md.
    normalized_on_disk = {i.lstrip("0") for i in on_disk}

    for claim in manifest.claims:
        for adr_id in claim.adrs:
            if adr_id.lstrip("0") not in normalized_on_disk:
                violations.append(
                    AdrViolation(
                        f"claims[{claim.id}]",
                        f"references ADR-{adr_id}, which does not exist in {ADR_DIR}",
                    )
                )

    return violations