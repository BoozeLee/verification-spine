# ADR-0001: The manifest is JSON, not YAML

- **Status:** accepted
- **Date:** 2026-10-07
- **Deciders:** kilisan
- **Binds:** every repository that adopts the spine, and `spine-check` itself

## Context

The spec (2026-10-07, §3) specified `spine.manifest.yaml`. That conflicts with a
second requirement in the same spec: §5 requires `spine-check` to be Python,
**stdlib only**, matching `harness` so it installs with `uv tool install`.

YAML has no stdlib parser. Supporting the spec's format literally means either
adding PyYAML — breaking the stdlib constraint, and adding a supply-chain
dependency to the one tool whose entire value is being trustworthy — or writing a
YAML subset parser, which is a worse outcome than either.

`json` is in the stdlib, is unambiguous about types, and every prospective adopter
already has tooling that reads it.

## Decision

The manifest is `spine.manifest.json`. This deviates from spec §3.

## Verification

`pytest tests/test_models.py` — the parser reads JSON and rejects everything the
schema does not permit. Run `spine-check . --claims --adrs --ci` against this
repository: the claim below runs it, so the format is exercised on every CI run.

## Consequences

- `spine-check` stays dependency-free and installable with no build step.
- Contributors cannot use YAML anchors or comments. For a file whose whole job is
  to be machine-checked, anchors that hide structure are a liability anyway.
- Anyone reading spec §3 expecting `.yaml` will be wrong; this ADR supersedes
  that line and is linked from the spec's Global Constraints.
