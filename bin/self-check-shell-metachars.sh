#!/bin/sh
# Claim: shell metacharacters in a verify command are rejected, never silently
# passed. This is the false-pass bug found while building Task 4; the manifest
# cannot regress it.
set -e
PYTHONPATH=src python3 - <<'PY'
import sys
from pathlib import Path
from spine_check.models import Claim
from spine_check.runner import Outcome, run_verify

bad = ["./verify.sh && false", "./verify.sh; false", "echo $(false)"]
for cmd in bad:
    outcome = run_verify(
        Claim(id="probe", statement="s", verify=cmd, expect="exit 0", timeout=10),
        Path("."),
    )
    if outcome.outcome is not Outcome.FAIL:
        sys.exit(f"{cmd!r} produced {outcome.outcome.value}, expected FAIL")
print(f"all {len(bad)} shell-metacharacter commands correctly rejected")
PY
