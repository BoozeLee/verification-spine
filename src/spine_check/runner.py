"""Running a claim's `verify` command and classifying what came back.

Owns: subprocess execution and the four outcomes. Knows nothing about policy —
whether a skip is acceptable is `cli.py`'s decision.

The load-bearing rule here is that nothing ambiguous can be mistaken for success:
a hang is TIMEOUT, "collected no tests" is SKIP, and a missing binary is FAIL.
Only a real exit 0 is PASS.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from spine_check.models import Claim

#: Exit codes that mean "the command ran but proved nothing". 5 is the
#: pytest / "no tests collected" convention shared by most test runners. It is
#: the ONLY reserved code — anything else non-zero is an ordinary failure.
SKIP_EXIT_CODES: frozenset[int] = frozenset({5})

#: Output is retained for the report but truncated so a runaway command cannot
#: blow up memory or the terminal.
MAX_CAPTURE = 4000

#: Shell composition is NOT supported in v1. `shlex.split("./verify.sh && false")`
#: yields `["./verify.sh", "&&", "false"]`, and because most scripts ignore their
#: arguments that exits 0 — a false PASS for a claim that fails in any real shell.
#: Rather than widen to `shell=True`, reject the command loudly and tell the
#: author to wrap it in a script they can read.
SHELL_METACHARACTERS = re.compile(r"&&|\|\||[;|><`]|\$\(|[&\n]")


class Outcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    TIMEOUT = "TIMEOUT"


@dataclass(frozen=True)
class ClaimOutcome:
    claim_id: str
    outcome: Outcome
    exit_code: int | None
    stdout: str = ""
    stderr: str = ""

    @property
    def passed(self) -> bool:
        return self.outcome is Outcome.PASS

    def describe(self) -> str:
        if self.outcome is Outcome.TIMEOUT:
            return "TIMEOUT"
        return f"{self.outcome.value} (exit {self.exit_code})"


def _truncate(text: str) -> str:
    if len(text) <= MAX_CAPTURE:
        return text
    return text[:MAX_CAPTURE] + f"\n… truncated, {len(text) - MAX_CAPTURE} more characters"


def run_verify(claim: Claim, repo_root: Path) -> ClaimOutcome:
    """Execute `claim.verify` with `repo_root` as cwd and classify the result.

    Never raises for a bad command: a missing binary, a non-executable script
    and a timeout are all outcomes, because a checker that crashes is a checker
    that can be made to pass by breaking it.
    """
    repo_root = Path(repo_root)
    if SHELL_METACHARACTERS.search(claim.verify):
        return ClaimOutcome(
            claim.id,
            Outcome.FAIL,
            None,
            stderr=(
                "shell composition is not supported in spine v1 — put the logic in a "
                "committed script and point `verify` at it, e.g. \"./verify.sh\""
            ),
        )

    try:
        argv = shlex.split(claim.verify)
    except ValueError as exc:
        return ClaimOutcome(claim.id, Outcome.FAIL, None, stderr=f"unparseable command: {exc}")

    if not argv:
        return ClaimOutcome(claim.id, Outcome.FAIL, None, stderr="empty verify command")

    try:
        proc = subprocess.run(
            argv,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=claim.timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return ClaimOutcome(
            claim.id,
            Outcome.TIMEOUT,
            None,
            _truncate(exc.stdout or ""),
            _truncate(exc.stderr or "") or f"exceeded {claim.timeout}s",
        )
    except (FileNotFoundError, PermissionError, OSError) as exc:
        return ClaimOutcome(claim.id, Outcome.FAIL, None, stderr=f"{type(exc).__name__}: {exc}")

    code = proc.returncode
    if code in SKIP_EXIT_CODES:
        outcome = Outcome.SKIP
    elif code == 0:
        outcome = Outcome.PASS
    else:
        outcome = Outcome.FAIL

    return ClaimOutcome(
        claim.id,
        outcome,
        code,
        _truncate(proc.stdout or ""),
        _truncate(proc.stderr or ""),
    )