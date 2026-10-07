"""Manifest parsing and static validation.

Owns: reading `spine.manifest.json`, turning it into typed objects, and
rejecting anything a claim needs in order to be checkable. Knows nothing about
running commands — that is `runner.py`.

Rule R1 lives here: every claim names a `verify` command a third party can run.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

MANIFEST_NAME = "spine.manifest.json"
SUPPORTED_VERSION = 1
DEFAULT_TIMEOUT = 300

_TOP_LEVEL_KEYS = {"project", "spine_version", "claims"}
_CLAIM_KEYS = {"id", "statement", "verify", "expect", "timeout", "evidence", "adrs"}
_REQUIRED_CLAIM_KEYS = ("id", "statement", "verify", "expect")


class ManifestError(Exception):
    """A manifest is missing, unparseable, or violates the schema.

    `.path` is the JSON key path of the offending value (`claims[2].verify`) so
    the message points at the thing, not the file. `.line` is the 1-based line
    in the raw manifest text where that key appears, when it can be located.
    """

    def __init__(self, reason: str, path: str = "", line: int | None = None):
        self.reason = reason
        self.path = path
        self.line = line
        where = path or "<manifest>"
        if line is not None:
            where = f"{where} (line {line})"
        super().__init__(f"{reason} [{where}]")


@dataclass(frozen=True)
class Claim:
    id: str
    statement: str
    verify: str
    expect: str
    timeout: int = DEFAULT_TIMEOUT
    evidence: str | None = None
    adrs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Manifest:
    project: str
    spine_version: int
    claims: list[Claim]
    path: Path | None = None


def _line_of(raw: str, key: str, occurrence: int = 0) -> int | None:
    """Best-effort line number for the nth occurrence of a JSON key.

    Textual, not a real parse — good enough to point a human at the line, and it
    never raises. If the key is absent, returns None and the caller omits it.
    """
    seen = -1
    for i, line in enumerate(raw.splitlines(), start=1):
        if re.search(rf'"{re.escape(key)}"\s*:', line):
            seen += 1
            if seen == occurrence:
                return i
    return None


def load_manifest(repo_root: Path) -> Manifest:
    """Read and validate `<repo_root>/spine.manifest.json`.

    Raises ManifestError for anything that would make a claim unverifiable. A
    missing or malformed manifest is an error here, not an exception escaping to
    the caller — `cli.py` turns it into exit code 2.
    """
    repo_root = Path(repo_root)
    manifest_path = repo_root / MANIFEST_NAME

    if not manifest_path.is_file():
        raise ManifestError(f"no {MANIFEST_NAME} in this repository", str(repo_root))

    raw = manifest_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ManifestError(
            f"manifest is not valid JSON: {exc.msg}",
            MANIFEST_NAME,
            exc.lineno,
        ) from exc

    if not isinstance(data, dict):
        raise ManifestError("manifest root must be a JSON object", MANIFEST_NAME, 1)

    unknown = sorted(set(data) - _TOP_LEVEL_KEYS)
    if unknown:
        raise ManifestError(
            f"unknown top-level key(s): {', '.join(unknown)}",
            unknown[0],
            _line_of(raw, unknown[0]),
        )

    version = data.get("spine_version")
    if version != SUPPORTED_VERSION:
        raise ManifestError(
            f"unsupported spine_version {version!r} (this checker speaks {SUPPORTED_VERSION})",
            "spine_version",
            _line_of(raw, "spine_version"),
        )

    project = data.get("project")
    if not isinstance(project, str) or not project.strip():
        raise ManifestError("missing or empty 'project'", "project", _line_of(raw, "project"))

    claims_raw = data.get("claims")
    if not isinstance(claims_raw, list):
        raise ManifestError(
            "'claims' must be a list", "claims", _line_of(raw, "claims")
        )

    claims: list[Claim] = []
    seen: dict[str, int] = {}

    for i, entry in enumerate(claims_raw):
        key_path = f"claims[{i}]"
        if not isinstance(entry, dict):
            raise ManifestError("each claim must be an object", key_path, _line_of(raw, "id"))

        extra = sorted(set(entry) - _CLAIM_KEYS)
        if extra:
            raise ManifestError(
                f"unknown claim key(s): {', '.join(extra)}",
                f"{key_path}.{extra[0]}",
                _line_of(raw, extra[0], i),
            )

        for required in _REQUIRED_CLAIM_KEYS:
            value = entry.get(required)
            if not isinstance(value, str) or not value.strip():
                raise ManifestError(
                    f"missing or empty {required!r}",
                    f"{key_path}.{required}",
                    _line_of(raw, required, i),
                )

        claim_id = entry["id"]
        if claim_id in seen:
            raise ManifestError(
                f"duplicate claim id {claim_id!r} (first seen at claims[{seen[claim_id]}])",
                f"{key_path}.id",
                _line_of(raw, "id", i),
            )
        seen[claim_id] = i

        expect = entry["expect"]
        if expect != "exit 0":
            raise ManifestError(
                f"unsupported expect {expect!r} (only 'exit 0' is defined in v1)",
                f"{key_path}.expect",
                _line_of(raw, "expect", i),
            )

        timeout = entry.get("timeout", DEFAULT_TIMEOUT)
        if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
            raise ManifestError(
                f"timeout must be a positive integer, got {timeout!r}",
                f"{key_path}.timeout",
                _line_of(raw, "timeout", i),
            )

        evidence = entry.get("evidence")
        if evidence is not None and not isinstance(evidence, str):
            raise ManifestError(
                "evidence must be a string path or null",
                f"{key_path}.evidence",
                _line_of(raw, "evidence", i),
            )

        adrs = entry.get("adrs", [])
        if not isinstance(adrs, list) or not all(isinstance(a, str) for a in adrs):
            raise ManifestError(
                "adrs must be a list of ADR id strings",
                f"{key_path}.adrs",
                _line_of(raw, "adrs", i),
            )

        claims.append(
            Claim(
                id=claim_id,
                statement=entry["statement"],
                verify=entry["verify"],
                expect=expect,
                timeout=timeout,
                evidence=evidence,
                adrs=list(adrs),
            )
        )

    return Manifest(
        project=project, spine_version=version, claims=claims, path=manifest_path
    )