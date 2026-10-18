# Spec — release spine-check 0.1.0

**Date:** 2026-10-17
**Status:** approved by the owner — this repository was selected for shipping in
the supervised engineering mission of 2026-10-17
**Driver:** [ADR-0003](../docs/adr/ADR-0003-release-not-construction.md)

## Problem

The tool is finished and rested (ADR-0002) but undistributable: no versioned
artifact, no release path, and an adoption story that requires cloning a
private repository. The publishing `hold` recorded in `PLANS.md` was awaiting a
human decision; on 2026-10-17 the owner selected this repository as the project
to ship. That decision is the new instruction the blocker asked for.

## Users

1. A repository author adopting the spine (primary; see `spec/ADOPTING.md`).
2. A CI integrator wiring the gate into a pipeline.

## Scope — release engineering only

- A versioned, reproducible artifact: sdist + wheel built from the tagged tree.
- A release claim in the self-manifest: the wheel installs into an empty
  environment and discriminates — accepts a conformant repository, rejects a
  broken one — with a declared mutation proving the check can fail.
- A tagged-release workflow (GitHub Releases; PyPI deliberately absent).
- Documentation accuracy: README numbers, CHANGELOG, install path.

## Non-goals

- No feature work, no Wave 2 harness integration — ADR-0002 stands.
- No PyPI publication in this release; it stays blocked on a written reversal
  of the `hold` (the GitHub release alone already publishes the artifact).
- No change to the checker's semantics, manifest schema, or exit codes.
- No Windows/macOS claims beyond extending the existing Linux CI matrix.

## Acceptance criteria

| # | criterion | verified by |
|---|---|---|
| AC1 | suite green, self-check green, no leaks | `pytest -q` (90), `./bin/spine-check . --claims --adrs --ci`, `gitleaks detect` |
| AC2 | the release claim passes and is non-vacuous | `./bin/spine-check . --vacuity` → `VERIFIED flip-rate 1/1` |
| AC3 | tag `v0.1.0` yields a GitHub release with sdist + wheel | `.github/workflows/release.yml` (verifiable only after the approved push) |
| AC4 | docs state the truth | README matches measured numbers; CHANGELOG carries 0.1.0 |

## Risks

- The release claim adds roughly a minute to CI (build + fresh venv). Accepted:
  it is what makes "releasable" a checked property instead of a memory.
- First public exposure of an AGPL tool. Mitigation: argv-only execution,
  stdlib-only runtime, no network, and clean `gitleaks`/`semgrep` scans,
  recorded in `harness/build-log.md`.
