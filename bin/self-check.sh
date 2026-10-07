#!/bin/sh
# Claim: "the-spine-checks-itself" — spine-check genuinely works.
#
# The first version of this script ran `pytest -q` and never invoked
# spine-check, so the claim was coupled to nothing: by this repo's own rules it
# was GREEN at best, and VACUOUS if it had declared a mutate. Running
# `spine-check .` here instead would recurse — spine-check reads this manifest,
# runs this claim, which runs spine-check again.
#
# So the claim is exercised against FIXTURES: a conformant repo must pass, and
# four deliberately broken repos must each be rejected. That is what makes it
# non-vacuous, and it is what `bin/mutate-self.sh` attacks.
set -e

fail() { echo "SELF-CHECK FAILED: $1" >&2; exit 1; }

# Anchored to this script, not to $PWD. A relative $CHECK silently became
# "exit 127: not found" after step 4 cd'd away, and since every rejection test
# is written `cmd && fail`, a missing binary looks exactly like a correct
# rejection. Step 4 therefore never invoked spine-check at all.
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CHECK="$HERE/spine-check"
F="$HERE/../tests/fixtures"

# Preflight: a gate that cannot run its own command must say so, not pass.
[ -x "$CHECK" ] || fail "spine-check is not executable at $CHECK"

# 1. a conformant repository must be accepted
"$CHECK" "$F/repo_ok" --claims --adrs --ci >/dev/null || fail "a conformant repo was rejected"

# 2. a broken claim must be rejected
"$CHECK" "$F/repo_fail" --claims --ci >/dev/null && fail "a failing claim was accepted"

# 3. a vacuous claim (passes, but a mutation breaks it and it still passes)
"$CHECK" "$F/repo_mutant_vacuous" --claims --vacuity --ci >/dev/null \
  && fail "a vacuous claim was accepted"

# 4. a trivial claim (`true`) must be denied
"$CHECK" "$F/repo_ok" --claims --vacuity --ci >/dev/null || true   # repo_ok is conformant
mkdir -p /tmp/spine-selfcheck && cd /tmp/spine-selfcheck
printf '{"project":"trivial","spine_version":1,"claims":[{"id":"t","statement":"s","verify":"true","expect":"exit 0"}]}' > spine.manifest.json
"$CHECK" . --claims --vacuity --ci >/dev/null && fail "a `true`-backed claim was accepted"
cd - >/dev/null

# 5. an ADR without ## Verification must be rejected
"$CHECK" "$F/repo_bad_adrs" --adrs >/dev/null && fail "an unverified ADR was accepted"

echo "self-check: spine-check accepts the conformant repo and rejects all four broken ones"
