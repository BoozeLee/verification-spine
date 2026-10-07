# ROADMAP — verification spine

Built 2026-10-07. Wave 1 only. Everything below Wave 1 is conditional on
evidence, not scheduled.

## Status

| phase | state | note |
|---|---|---|
| Spec | approved in conversation, **jev round 2 = NOT APPROVED (0.89)** | thesis provisional at 0.71 |
| Wave 1 · tasks 1–5 | **done** | `spine-check` builds, self-checks, 77 tests |
| Wave 1 · task 6 (adopt on `elohim`) | **deferred to after 2026-10-13** | jev `after_screening` 0.95 |
| Wave 2 (`harness` integration) | conditional | not scheduled |
| Wave 3 (remaining repos) | conditional | not scheduled |

## What exists

```
verification-spine/
  bin/spine-check                 self-locating shim, works from any cwd
  src/spine_check/models.py       manifest parsing, schema validation (R1)
  src/spine_check/runner.py       verify execution, 4 outcomes (R2)
  src/spine_check/adrs.py         ## Verification enforcement (R3)
  src/spine_check/vacuity.py      denylist + mutation campaigns (B3)
  src/spine_check/cli.py          flags and exit code
  spine.manifest.json             the spine's own two claims
  spec/conformance.md             adoption guide + what the tool does NOT check
  VISION.md  README.md
  docs/adr/                       starts with ADR-0001 (JSON not YAML)
```

## Findings worth keeping

Three bugs found by testing this tool against itself, none of which any
earlier assertion would have caught:

- **A false pass.** `./verify.sh && false` was reported **PASS**. `shlex.split`
  made it three argv entries, the script ignored two and exited 0. A claim that
  fails in any real shell was certified true. This is the exact failure the
  spine exists to prevent, present in the spine.
- **An unusable tool.** Every one of 40 tests passed while
  `./bin/spine-check` — the command a user actually types — died with
  `No module named spine_check`, because the tests imported the package rather
  than running the shim.
- **A mutation that outlived its run.** Restore used `git checkout -- .`, which
  silently does nothing for untracked files. A mutated fixture poisoned the next
  run. Caught by running the suite three times and diffing, not by any
  assertion.

## Known limits, stated plainly

- It cannot tell whether a `verify` command is the *semantically right* one for
  its statement. See `spec/conformance.md`.
- `evidence` is parsed and ignored.
- No cross-repo claims; `verify` runs with the repo root as cwd.
- `--vacuity` is deliberately not run in CI on this repo: its claims cannot
  mutate themselves, and forcing one would recurse or manufacture false
  findings.

## Next

Ordered by leverage, not interest.

1. **After 2026-10-13 — adopt on `elohim`.** Suite is green (319 passed,
   1 skipped), so the gate rule permits it. Two claims, two ADRs, one CI job.
   Expect the `verify` command to need to be `python3 tests/test_all.py`, not
   bare `pytest`, because that is what elohim's CI actually runs.
2. **Fix `agentic-setup/templates/ADR-template.md`.** It has no `## Verification`
   section, so an ADR written faithfully from it fails R3. This is the highest
   value item here and it is a five-minute edit that unblocks every adopter.
3. **Decide `~/workspace/foundation-ai-engine/`.** Nine vendored dependencies, no
   source, no git history. An abandoned second foundation. Delete or mark
   archived — currently ambiguous, which is its own problem.
4. **Only then Wave 2** — teach `harness` to invoke `spine-check`, so the gate
   runner does not need a sibling.
5. **Push this repo.** It has ten commits, no remote, and is one disk failure
   from gone. Deferred pending the user's word, like every other push.

## Kill criterion, unchanged

If `spine-check` is not used by two repositories within two weeks of adoption
starting, the spine is killed and the per-repo ADRs are kept. jev scored this
criterion 0.63 — a weak endorsement of a weak gate. It is retained rather than
loosened because it is the only mechanism stopping this becoming the ninth
unused document on this machine.