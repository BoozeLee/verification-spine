# Changelog

All notable changes to `spine-check`. Format follows Keep a Changelog;
versioning is semver.

## [0.1.1] - 2026-10-21

Packaging-quality release: no behavior changes to checking, one hardening
change to `--vacuity` (below).

### Added

- `spine-check --version` — the version comes from the package itself
  (`src/spine_check/__init__.py`), which is now the single source consumed by
  pyproject (hatchling dynamic version), the wheel metadata, and the CLI.
- Full PyPI-grade package metadata: readme, author, keywords, classifiers,
  and project URLs (repository, changelog, releases, issue tracker).
- `SECURITY.md`, `CONTRIBUTING.md` (including the compatibility policy), and
  `CODE_OF_CONDUCT.md`.
- Build provenance: the release workflow now attests the wheel with
  `actions/attest-build-provenance` (SLSA) — verify a download with
  `gh attestation verify <file> -R BoozeLee/verification-spine`.

### Changed

- README no longer hardcodes the test count (it drifted twice: 77 → 90 → 91).

### Hardened

- `--vacuity` refuses to snapshot repositories over 64 MiB: the only honest
  verdict is `UNPROVABLE`, and `mutate` never runs. Previously an oversized
  repository could exhaust memory during a mutation campaign.

## [0.1.0] - 2026-10-17

First release. Built 2026-10-07 and deliberately rested (ADR-0002); released
without feature changes (ADR-0003).

### Added

- `spine-check` CLI: manifest claims (`--claims`), ADR enforcement (`--adrs`),
  mutation vacuity (`--vacuity`), CI mode (`--ci`), per-claim timeouts, and the
  exit-code contract (0 all-pass · 1 failed/vacuous/denied/skipped · 2 unusable
  manifest or ADR violation).
- `spine.manifest.json` v1 schema: per-claim `id`, `statement`, `verify`,
  `mutate`, `expect`, `timeout`, `evidence`, `adrs`.
- Four-state claim reporting: `verified` / `green` / `vacuous` / `unprovable` /
  `denied` / `broken`, with flip rates from declared mutations.
- Self-adoption: this repository checks itself in CI, including a
  planted-defect negative control and a release claim whose wheel must install
  into an empty environment and discriminate conformant from broken repos.
- Release engineering: versioned sdist + wheel, tagged-release workflow with a
  wheel smoke test, this changelog.

### Fixed

- Shell composition (`&&`, `;`, `||`, `$()`, backticks) in `verify` is rejected
  instead of silently mis-parsed into argv — the false-PASS bug found by
  running the tool against itself.
- The entry-point shim self-locates and needs no `PYTHONPATH`; the first
  version shipped with the whole suite green while the CLI a user actually
  typed was broken.
- Mutation restore is snapshot-based; `git checkout -- .` silently leaked
  untracked mutations into subsequent runs, and empty directory shells
  survived restore.

### Security

- `verify` executes as argv with the repository root as cwd; shell
  metacharacters are rejected, never reinterpreted.
- Output capture is capped at 4,000 characters per stream so a runaway command
  cannot exhaust memory or the terminal.
- Stdlib-only runtime: no third-party dependencies, no network access.
