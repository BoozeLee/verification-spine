# Work plan index

**This file owns current task status.** Individual plans own their approach and
acceptance criteria; the build log owns execution evidence.

A cold session should be able to state what is happening and what to do next from
this file alone, without reading a single transcript.

## Current work

<!-- Status vocabulary — use these words, they are what session-close.sh greps for:
     planned | in progress | blocked (reason) | complete -->

No implementation task is currently active.

That is a decision, not an oversight. jev-1.13.0 returned **`stopped`** as the end
goal for this work (stop 0.81; ship 0.01 · adopt 0.01 · harden 0.17), recorded in
[ADR-0002](docs/adr/ADR-0002-the-spine-is-complete-and-rests.md). Building stopped
there deliberately. Wave 2 (`harness` integration) and Wave 3 (remaining repos) are
conditional on observable use, not on a date.

The survival rule, replacing the withdrawn kill criterion: **the spine survives
while a claim it certifies is still being read by someone other than its author.**
It ends when no repo outside this one runs it, or when its author stops believing
it — whichever comes first. There is no deadline, because a deadline rewards
adoption that nobody needed.

## Planning convention

For substantial work, create `harness/build/<number>-<task>.md` with the outcome,
scope, ordered implementation steps, acceptance checks, and rollback. Add its status
here. Small changes can use the user request directly without new planning files.

Update task status and evidence with the logical change. **Commit only when asked.**

When a task is complete, move it below and link the evidence. Do not leave a
completed task sitting in "Current work" — a stale status is worse than none.

## Completed

- **Wave 1 · tasks 1–5 (build the tool)**: complete. Plan:
  [docs/superpowers/plans/2026-10-07-verification-spine-wave1.md](docs/superpowers/plans/2026-10-07-verification-spine-wave1.md).
  Evidence: [harness/build-log.md](harness/build-log.md).
- **Wave 1 · task 6 (adopt on `elohim`)**: complete 2026-10-07, superseding the
  earlier `deferred to after 2026-10-13` status in ROADMAP.md. `elohim` carries
  `spine.manifest.json` (2 claims) and `ADR-0001`/`ADR-0002`, committed as
  `96d59b5`. Gate rule checked first: `python3 tests/test_all.py` → `ALL_SKILLS_PASS`.
  Evidence: [harness/build-log.md](harness/build-log.md).

## Blocked

| Task | Blocker | Owner | Escape hatch |
|---|---|---|---|
| Run `spine-check` in `elohim`'s CI | `elohim` is **public**; this repo is **private** and deliberately so (it ships an AGPL tool nobody has vetted for public release). Public-repo CI cannot clone a private repo without a PAT, and a PAT in public CI is a bad design. jev-1.13.0 ruled **`hold`** on publishing to PyPI (0.98), so no `pip install` path either. | human | Nothing ships broken: `elohim`'s own gate `python3 tests/test_all.py` already passes, the manifest and both ADRs are committed, and the job-to-add is written down in `elohim`'s `ADR-0001`. The blocker costs CI enforcement, not correctness. |

Unblocking requires a human decision — make this repo public, or publish
`spine-check` to PyPI, or accept a PAT. Both published options were declined for
now; do not re-litigate without a new instruction.