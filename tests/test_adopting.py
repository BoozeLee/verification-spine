"""spec/ADOPTING.md must be executable, not aspirational.

The walkthrough is the thing an adopter actually follows. jev scored the
predecessor document 0.58 for being too implicit to adopt from alone, so this
test performs the walkthrough against a throwaway repository: every command the
guide tells an adopter to run is run here, and the guide's own snippets are
extracted and checked for drift against the real CLI.

If the guide goes stale, this fails rather than lying.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
GUIDE = REPO / "spec" / "ADOPTING.md"
SHIM = REPO / "bin" / "spine-check"


def _sh(*args, cwd, expect=0):
    """Run the CLI the way the guide tells an adopter to."""
    proc = subprocess.run(
        [str(SHIM), *args], cwd=cwd, capture_output=True, text=True, timeout=180
    )
    assert proc.returncode == expect, (
        f"spine-check {' '.join(args)} in {cwd}\n"
        f"expected exit {expect}, got {proc.returncode}\n"
        f"stdout={proc.stdout}\nstderr={proc.stderr}"
    )
    return proc


@pytest.fixture
def adopted(tmp_path):
    """Perform the whole walkthrough: manifest, verify.sh, ADR. Nothing else."""
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    (tmp_path / "spine-verify.sh").write_text("#!/bin/sh\nexit 0\n")
    (tmp_path / "spine-verify.sh").chmod(0o755)
    (tmp_path / "spine.manifest.json").write_text(
        json.dumps(
            {
                "project": "adopted-fixture",
                "spine_version": 1,
                "claims": [
                    {
                        "id": "suite-passes",
                        "statement": "Every test in this repository passes.",
                        "verify": "./spine-verify.sh",
                        "expect": "exit 0",
                        "adrs": ["0001"],
                    }
                ],
            },
            indent=2,
        )
    )
    (tmp_path / "docs" / "adr" / "ADR-0001-suite-passes.md").write_text(
        "# ADR-0001: The suite passes\n\n"
        "- **Status:** accepted\n\n"
        "## Context\nIt should.\n\n"
        "## Decision\nShip only green.\n\n"
        "## Verification\n"
        "`./spine-verify.sh` — exits 0 while the suite passes.\n\n"
        "## Consequences\nFewer merges.\n"
    )
    return tmp_path


# --- the guide itself ---------------------------------------------------------

def test_guide_exists_and_is_substantial():
    assert GUIDE.is_file(), "spec/ADOPTING.md is the top item on the follow-up plan"
    assert len(GUIDE.read_text()) > 2000


def test_every_flag_the_guide_mentions_really_exists():
    """Doc drift: a flag documented but not implemented sends adopters nowhere."""
    text = GUIDE.read_text()
    helped = subprocess.run(
        [str(SHIM), "--help"], capture_output=True, text=True, timeout=120
    ).stdout
    for flag in sorted(set(re.findall(r"`(--[a-z-]+)", text))):
        assert flag in helped, f"{flag} is documented in ADOPTING.md but does not exist"


def test_guide_states_what_it_does_not_check():
    """The most important section. Losing it would be the worst possible drift."""
    text = GUIDE.read_text()
    assert "does not check" in text
    for topic in ("semantically right", "evidence", "Prose", "Cross-repo"):
        assert topic in text, f"ADOPTING.md no longer names the limit: {topic}"
    assert "Security" in text and "pull request" in text


# --- the walkthrough ----------------------------------------------------------

def test_step_5_accepts_a_conformant_repository(adopted):
    _sh(".", "--claims", "--adrs", "--ci", cwd=adopted)


def test_step_5_negative_control_actually_goes_red(adopted):
    """The guide tells adopters to break their verify script and expect exit 1.

    If that does not happen, the guide is teaching a ritual that proves nothing.
    """
    script = adopted / "spine-verify.sh"
    original = script.read_text()
    try:
        script.write_text("#!/bin/sh\nexit 1\n")
        script.chmod(0o755)
        _sh(".", "--claims", "--ci", cwd=adopted, expect=1)
    finally:
        script.write_text(original)
        script.chmod(0o755)
    _sh(".", "--claims", "--ci", cwd=adopted)


def test_an_adr_missing_verification_is_rejected(adopted):
    adr = adopted / "docs" / "adr" / "ADR-0001-suite-passes.md"
    kept = adr.read_text()
    try:
        adr.write_text(
            "\n".join(
                ln for ln in kept.splitlines() if not ln.startswith("## Verification")
            )
            + "\n"
        )
        proc = _sh(".", "--adrs", cwd=adopted, expect=2)
        assert "documentation, not a constraint" in proc.stdout
    finally:
        adr.write_text(kept)


def test_step_7_mutation_moves_a_claim_to_verified(tmp_path):
    """The section the guide calls 'the valuable part'."""
    for sub in ("docs/adr",):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "subject.py").write_text('SUBJECT = "intact"\n')
    (tmp_path / "spine-verify.sh").write_text(
        '#!/bin/sh\ngrep -q \'SUBJECT = "intact"\' subject.py\n'
    )
    (tmp_path / "spine-mutate.sh").write_text(
        '#!/bin/sh\nsed -i \'s/intact/broken/\' subject.py\n'
    )
    for f in ("spine-verify.sh", "spine-mutate.sh"):
        (tmp_path / f).chmod(0o755)
    (tmp_path / "spine.manifest.json").write_text(
        json.dumps(
            {
                "project": "mutation-fixture",
                "spine_version": 1,
                "claims": [
                    {
                        "id": "coupled",
                        "statement": "The subject is intact.",
                        "verify": "./spine-verify.sh",
                        "mutate": "./spine-mutate.sh",
                        "expect": "exit 0",
                    }
                ],
            }
        )
    )
    proc = _sh(".", "--claims", "--vacuity", cwd=tmp_path)
    assert "VERIFIED" in proc.stdout, proc.stdout
    assert "flip-rate 1/1" in proc.stdout, proc.stdout
    assert (tmp_path / "subject.py").read_text() == 'SUBJECT = "intact"\n'


def test_the_snippets_in_the_guide_parse_as_valid_manifests():
    """A JSON snippet an adopter copies must not be malformed."""
    text = GUIDE.read_text()
    blocks = re.findall(r"```json\n(.*?)```", text, re.S)
    assert blocks, "the guide shows no JSON examples"
    # Only whole-object blocks are manifests; the guide also shows a one-line
    # fragment (`"mutate": …`) that is meant to be pasted into a claim.
    manifests = [b for b in blocks if b.lstrip().startswith("{")]
    assert manifests, "the guide shows no complete manifest example"
    for i, block in enumerate(manifests, 1):
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError as exc:
            pytest.fail(f"manifest block #{i} in ADOPTING.md does not parse: {exc}")
        assert parsed.get("spine_version") == 1, f"manifest #{i} has no spine_version"
        assert isinstance(parsed.get("claims"), list), f"manifest #{i} has no claims"