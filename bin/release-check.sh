#!/bin/sh
# Claim: "release-artifact-installs-and-behaves".
#
# The artifact we would publish must install into an empty environment and
# discriminate: reject a deliberately broken repository, accept a conformant
# one. Both controls run against FIXTURES — running the installed tool against
# this repository would recurse (it would re-enter this manifest's claims),
# which is the same reason bin/self-check.sh stays on fixtures.
#
# The build goes to a throwaway directory, not ./dist: the claim must hold on a
# clean tree, and a stale dist/ must never be able to make it pass.
set -eu

ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT INT TERM
cd "$ROOT"

fail() { echo "release-check FAILED: $1" >&2; exit 1; }

# 1. build sdist + wheel (uv when present; PEP 517 build otherwise)
if command -v uv >/dev/null 2>&1; then
  uv build --out-dir "$TMP/dist" >/dev/null || fail "uv build failed"
else
  python3 -m build --outdir "$TMP/dist" >/dev/null || fail "python -m build failed"
fi

WHEEL=$(ls "$TMP"/dist/spine_check-*.whl 2>/dev/null || true)
[ -n "$WHEEL" ] || fail "no wheel was produced"

# 2. install into an empty environment (ensurepip provides pip offline)
python3 -m venv "$TMP/venv"
"$TMP/venv/bin/pip" install --quiet "$WHEEL" >/dev/null || fail "the wheel did not install"

# 3. the console script must exist and answer
"$TMP/venv/bin/spine-check" --help >/dev/null || fail "the installed entry point is broken"

# 4. negative controls: the installed tool must reject broken repositories
#    repo_fail carries a claim whose verify exits 1; repo_bad_adrs carries an
#    ADR with no enforcement. repo_tamper would be wrong here — it is
#    conformant until a defect is planted into it (the CI workflow plants one;
#    we do not).
"$TMP/venv/bin/spine-check" "$ROOT/tests/fixtures/repo_fail" --claims --ci >/dev/null 2>&1 \
  && fail "the installed wheel ACCEPTED a repository with a failing claim"

"$TMP/venv/bin/spine-check" "$ROOT/tests/fixtures/repo_bad_adrs" --adrs >/dev/null 2>&1 \
  && fail "the installed wheel ACCEPTED an unenforced ADR"

# 5. positive control: the installed tool must accept a conformant repository
"$TMP/venv/bin/spine-check" "$ROOT/tests/fixtures/repo_ok" --claims --adrs --ci >/dev/null \
  || fail "the installed wheel rejected a conformant repository"

echo "release-check: wheel builds, installs, and discriminates (rejects broken, accepts conformant)"
