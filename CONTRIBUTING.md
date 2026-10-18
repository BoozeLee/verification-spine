# Contributing

## Setup

Requires Python ≥ 3.10. Runtime dependencies: none (stdlib only) — that is a
design constraint (ADR-0001), not an accident. Tests use `pytest` as a dev
dependency only.

```bash
git clone https://github.com/BoozeLee/verification-spine
cd verification-spine
python3 -m pip install pytest        # or: uv tool install . for the CLI
python3 -m pytest -q
./bin/spine-check . --claims --adrs --ci   # the repo checks itself
```

## House rules

1. **No new runtime dependencies.** Stdlib only. A dev dependency needs a
   better reason than convenience.
2. **`verify` is argv, never shell.** Shell metacharacters are rejected, not
   reinterpreted — see `spec/conformance.md` for why composition was a real
   false-PASS bug here.
3. **Every binding decision gets an ADR with a working `## Verification`
   section** — the `--adrs` gate enforces this on every CI run, so an ADR
   without enforcement fails the build rather than shipping as prose.
4. **Tests stay deterministic** and fast; the suite includes mutation tests
   that must restore the tree byte-for-byte (`git diff --exit-code` in CI).
5. **Run the gates before every commit**: `pytest -q`, then
   `./bin/spine-check . --claims --adrs --ci`, then `--vacuity` if you touched
   mutation code.
6. **Commit style**: imperative subject line, body explains why. The changelog
   (`CHANGELOG.md`) records every released change.

## Releasing

Owned by the maintainer. A `v*` tag triggers the release workflow, which
builds the sdist and wheel, installs the wheel into a fresh environment, and
requires it to discriminate conformant from broken fixture repositories before
publishing the GitHub release (see `.github/workflows/release.yml`).
