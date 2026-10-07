#!/bin/sh
# Claim: the closing ruling is actually recorded, not merely asserted.
set -e
F="docs/adr/ADR-0002-the-spine-is-complete-and-rests.md"
[ -f "$F" ] || { echo "ADR-0002 missing" >&2; exit 1; }
grep -q '^## Verification' "$F" || { echo "ADR-0002 has no Verification section" >&2; exit 1; }
grep -q '0.81' "$F" || { echo "ADR-0002 does not record the score" >&2; exit 1; }
grep -q 'stopped' "$F" || { echo "ADR-0002 does not record the ruling" >&2; exit 1; }
echo "ADR-0002 records the ruling, its scores, and its own verification"
