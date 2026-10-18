# ADR-0003: The resting spine is released, not extended

- **Status:** accepted
- **Date:** 2026-10-17
- **Deciders:** kilisan
- **Binds:** release work on this repository; supersedes the publishing `hold`
  in `PLANS.md` (Blocked table) and the "private until vetted" caveat in
  `ROADMAP.md` item 4 — for this release only
- **Compatible with:** ADR-0002 — building stays stopped; nothing here resumes it

## Context

`PLANS.md` blocked publication behind a human decision: "make this repo public,
or publish `spine-check` to PyPI, or accept a PAT … do not re-litigate without
a new instruction." On 2026-10-17 the owner, working through a supervised
engineering mission, selected this repository as the one project to ship, at a
public v0.1.0. That is the new instruction the blocker asked for.

The vetting concern is answered by gates, not assurances: the test suite, the
self-check with its planted-defect negative control, mutation vacuity,
`gitleaks`, and `semgrep` — all re-run for this release and recorded in
`harness/build-log.md`.

Distribution is not construction. The tool is complete under ADR-0002; making
an artifact installable does not resume feature work. The release path is
itself a claim, so "releasable" stays a checked property instead of a memory.

## Decision

Release 0.1.0 as a tagged GitHub Release carrying the sdist and wheel built by
`.github/workflows/release.yml`. PyPI stays out of scope until the `hold` is
reversed in writing. The release path is claimed in `spine.manifest.json`
(`release-artifact-installs-and-behaves`), so a tag whose wheel cannot install
fails the same gate that runs on every push.

## Verification

`./bin/release-check.sh` — builds sdist and wheel from the working tree into a
throwaway directory, installs the wheel into a fresh venv, runs its
`spine-check --help`, then requires the installed tool to reject
`tests/fixtures/repo_fail` (a failing claim) and `tests/fixtures/repo_bad_adrs`
(an unenforced ADR), and to accept `tests/fixtures/repo_ok`. Non-vacuous by
construction: `./bin/mutate-release.sh` corrupts `pyproject.toml`, the build
must fail, and `./bin/spine-check . --vacuity` reports `VERIFIED flip-rate 1/1`
for the manifest claim `release-artifact-installs-and-behaves`.

## Consequences

- CI gains roughly a minute (build + fresh venv) and needs the `build` package
  on runners without `uv`.
- The repository becomes public at release time. AGPL was chosen for exactly
  this; nothing in the tree assumes privacy.
- A tag whose wheel misbehaves cannot be released silently: the smoke step
  fails the workflow before `gh release create` runs.
