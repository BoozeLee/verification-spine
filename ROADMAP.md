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
3. ~~Decide `~/workspace/foundation-ai-engine/`.~~ **RESOLVED 2026-10-07.** jev-1.13.0
   ruled **quarantine**, 0.93 confidence / 0.95 probability (delete 0.01, keep
   0.00) — the first >=0.9 ruling since `after_screening`, therefore acted on.
   It held 327M across 9 `BoozeLee/*` clones with **zero source files**, no git
   history, untouched since 2026-05-21. Moved to
   `~/_quarantine/2026-10-07/foundation-ai-engine` with 9 `git bundle`s of every
   dependency and `RESTORE-foundation-ai-engine.sh`. Reversible in one command.
4. **Only then Wave 2** — teach `harness` to invoke `spine-check`, so the gate
   runner does not need a sibling.
5. **Push this repo.** It has ten commits, no remote, and is one disk failure
   from gone. Deferred pending the user's word, like every other push.

## Decision rule — replaces the kill criterion

> **Withdrawn 2026-10-07.** The "2 repos within 2 weeks" criterion scored 0.63
> and then 0.36 with jev. Below 0.5 is *prior against, no action* — and
> defending a mechanism twice against a below-threshold verdict is not keeping a
> safeguard, it is keeping a rule nobody believes.

**The rule now:** the spine survives while a claim it certifies is still being
read by someone other than its author. It ends when no repo outside this one
runs it, or when its author stops believing it — whichever comes first.

There is no deadline, because a deadline rewards adoption that nobody needed.

Reversible by construction: ending the spine keeps every ADR, every manifest and
every gate. Nothing rolls back.

## Ruling this plan follows

`spec/CONFORMANCE-FOLLOWUP.md` — jev-1.13.0 on `conformance.md`, same day.
Adoption guide scored **0.58** (too implicit to follow alone), kill criterion
**0.36** (against), limits section **0.75** (candid, leave alone), keep-building
**0.61**, wave-1 value **0.50** (borderline). The work is `spec/ADOPTING.md` — a
walkthrough an engineer can actually follow — not more tool.
