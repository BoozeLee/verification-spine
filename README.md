# spine-check

> **Every claim carries re-runnable evidence.**

A stdlib-only Python CLI that reads a repository's `spine.manifest.json`, runs
each claim's verification command, and refuses to call a claim proven unless
its evidence could actually have failed.

No dependencies. No network. `git clone` and run.

```bash
./bin/spine-check . --claims --adrs --ci
```

## Why

A command that exits 0 proves it ran. It does not prove anything was checked —
`true` exits 0, and so does a test suite that collected nothing. Most gates
report that as green.

`spine-check` adds two things most gates lack:

1. **It reports state, not just a verdict.** A claim that has only ever passed is
   **green**. It becomes **verified** only when it has also been seen to fail.
2. **It checks that the evidence is coupled to the claim.** Declare a `mutate`
   that deliberately breaks the claim's subject; if `verify` still passes, the
   claim is **vacuous** and gets flagged.

```
$ spine-check . --claims --vacuity --ci
my-project (spine v1) — /home/kilisan/my-project
  claim residual-gate-holds: PASS (exit 0)
  vacuity residual-gate-holds: VERIFIED flip-rate 1/1
spine-check: OK
```

Against a claim backed by nothing:

```
  claim proves-anything: PASS (exit 0)
  vacuity proves-anything: DENIED
                                                    # exit 1
```

## Install

Requires Python ≥ 3.10. Nothing else.

```bash
git clone <this repo> && cd verification-spine
./bin/spine-check --help

# or as a package
uv tool install .
```

The shim resolves the package from its own location, so it works from any
directory without `PYTHONPATH`.

## Usage

| flag | effect |
|---|---|
| `--claims` | run each claim's `verify` command |
| `--vacuity` | run mutation campaigns — does `verify` notice when its subject breaks? |
| `--adrs` | require every ADR to name its enforcement |
| `--ci` | a skipped claim is a failure; an `UNPROVABLE` claim is a failure |
| `--timeout N` | override every claim's timeout |
| `--verbose` | include command output |

Exit `0` all-pass · `1` a claim failed, timed out, or is vacuous/denied ·
`2` manifest unusable or an ADR violation.

## Adopting it

Read [`spec/conformance.md`](spec/conformance.md) — including the section on what
this tool does **not** check, which matters more than what it does.
[`VISION.md`](VISION.md) has the reasoning.

Short version: your suite must be green first, then add `spine.manifest.json`,
then `docs/adr/`, then wire the CLI into CI.

```json
{
  "project": "my-project",
  "spine_version": 1,
  "claims": [
    {
      "id": "my-claim",
      "statement": "A sentence a reasonable person could disagree with.",
      "verify": "./verify.sh",
      "expect": "exit 0",
      "adrs": ["0001"]
    }
  ]
}
```

## Design notes

- **`verify` is argv, not shell.** Shell metacharacters are rejected, not
  reinterpreted. `./verify.sh && pytest` would split into three argv entries,
  the script would ignore two, exit 0, and certify a claim that fails in any
  real shell. That was a real bug here; see commit `591efbb`.
- **Mutation restores from a snapshot, not from git.** `git checkout -- .`
  silently does nothing for untracked files, so a mutation could outlive the run
  and poison the next one.
- **The spine adopts itself.** `spine-check . --claims --adrs --ci` runs against
  this repository on every CI run.

## Development

```bash
python3 -m pytest -q     # 77 tests
./bin/spine-check . --claims --adrs --vacuity --ci
```

Architecture, provenance and the jev decision record are in
`docs/superpowers/specs/2026-10-07-verification-spine-design.md`.