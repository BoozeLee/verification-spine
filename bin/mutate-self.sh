#!/bin/sh
# Corrupt spine-check itself so it always reports success.
#
# This is what makes the "the-spine-checks-itself" claim VERIFIED rather than
# GREEN: with cli.py neutered, bin/self-check.sh's negative controls (a broken
# claim, a vacuous claim, a `true`-backed claim, an unverified ADR) will no
# longer be rejected, so the claim flips to FAIL. If the mutation here stops
# making it fail, the claim has become vacuous and the spine is lying.
set -e
sed -i 's/^    return exit_code$/    return 0  # MUTATED/' src/spine_check/cli.py
grep -q 'MUTATED' src/spine_check/cli.py || { echo "mutation had no effect" >&2; exit 1; }
