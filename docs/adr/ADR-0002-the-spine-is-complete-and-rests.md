# ADR-0002: The spine is complete and rests

- **Status:** accepted
- **Date:** 2026-10-07
- **Deciders:** kilisan
- **Binds:** any future session tempted to resume `verification-spine`

## Context

`verification-spine` was built on 2026-10-07 to close a measured gap: across the
eight highest-scoring repositories on this machine, `docs/adr/` was empty, and
`agentic-setup/templates/ADR-template.md` had zero users. `agentic-setup/ROADMAP.md`
records the failure it was meant to prevent — *"a plan was written from the ledger
and jev ranking without reading this directory, then reverted against ADR-0022
and ADR-0025."*

Sixteen commits later the tool builds, self-verifies, and has found five bugs in
itself. It also accumulated an unfavourable record.

jev-1.13.0 was asked to judge `spec/conformance.md` and the project as a whole.
Across three rounds:

| question | round 1 | round 2 | final |
|---|---|---|---|
| is the spine thesis real? | 0.71 | — | — |
| ready to plan from? | — | 0.89 | — |
| adoption guide sufficient? | — | — | **0.58** |
| wave-1 value (elohim only)? | — | — | **0.50** |
| keep the kill criterion? | 0.63 | — | **0.36** |
| keep building vs stop? | 0.61 | — | **0.47** |
| **end goal for today's block** | — | — | **`stopped`, 0.75 conf / 0.81 prob** |

On the end goal: ship 0.01, adopt on elohim 0.01, harden 0.17, **stop 0.81**.
Adopting on elohim before the screening scored **0.15**. Fixing the symlink leak
by removing symlinks scored **0.16** — jev considers it the wrong fix.

Under the standing rule (`≥0.9` act as decided · `<0.5` prior against, no
action · `0.5–0.9` prior, reversible only), none of these reached a mandate, and
two fell below the threshold for action entirely.

## Decision

The spine is complete. Stop building it.

- `spec/ADOPTING.md` will not be written. jev scored the shipped at 0.01.
- The symlink leak in `restore_tree` will **not** be fixed. jev scored that fix
  0.16. An unfixed, unreached path is recorded here instead.
- The spine will not be adopted on `elohim` before the screening (0.15), and
  Wave 2 is dropped rather than deferred.
- The repository stays where it is. It is not deleted, and it is not quarantined.
  Sixteen commits with no remote are a backup risk, not a reason to destroy work.

What survives: the `## Verification` section added to
`agentic-setup/templates/ADR-template.md` on the same day, which unblocks every
adopter and does not depend on this tool existing.

## Verification

`jev run` over the project's code, tests, measured probe results and this
repository's own state, 2026-10-07 — returned `end_goal: stopped`, confidence
0.75, probability 0.81. The request and response are at `/tmp/jev-audit.json`
and `/tmp/jev-audit-resp.json`; they are not durable and will not survive a
reboot.

Until that is superseded, this ADR is the gate. A future session that resumes
spine work must first say what evidence has changed since 2026-10-07, because
"it was 81% to stop" is not a durable property of the world.

The template fix this decision preserves is verified directly:
`~/verification-spine/bin/spine-check <repo> --adrs` exits 0 on an ADR carrying
the new shape, 2 on the old five-section shape, and 0 on a superseded ADR.

## Consequences

**Accepted costs**
- The security exposure of `--vacuity` is documented, not mitigated. `mutate`
  runs arbitrary commands and writes to the working tree. Any CI wiring this
  tool into a fork's pull requests inherits that. Recorded here so it is a
  known property rather than a surprise.
- The tool has one adopter: itself.
- `spec/conformance.md` stays as written. jev scored its candour 0.75, its
  weakest section was the one nobody had to invent.

**Accepted benefits**
- The measurable gap — an ADR template that contradicted the rule it exists to
  propagate — is closed, and closed by a five-minute edit rather than by a
  codebase.

## Rejected alternatives

- **Fix the symlink leak (0.16).** Rejected. It hardens a path that, once the
  spine rests, only runs on this repository's own fixtures — while adding code
  that must itself be maintained.
- **Adopt on `elohim` first (0.15 for now).** Rejected until after 2026-10-13.
  Not rejected on merit: rejected on timing. The screening is six days away and
  the owner's own rule forbids new projects this month.
- **Continue hardening (0.17).** Rejected as the end goal.

## Revisit when

A second repository outside this one asks for the tool. That is the only signal
that would change the arithmetic — not elapsed time, and not enthusiasm.