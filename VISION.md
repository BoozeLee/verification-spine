# VISION

> **Every claim carries re-runnable evidence.**

A *claim* is a sentence a reasonable person could disagree with.
Its *evidence* is a command that passes or fails, runnable by someone who
does not trust the author.

This repository is the tool that holds you to it. The projects it will be
applied to are applications of the same idea: `elohim` gates a numerical claim
by its residual, `mcp-regression-lab` gates an MCP contract by its diff,
`hirebridge` gates a hiring claim by re-running the command that proves it.

## Why this exists

`~/agentic-setup/ROADMAP.md` records the failure that motivated it:

> *"S7 wrote a plan from the ledger and jev ranking, never checked `docs/adr/`,
> built three workstreams, then reverted against ADR-0022 and ADR-0025 — which
> were already enforced by a passing test."*

The diagnosis was written down. The fix was not. Across all eight top projects
on this machine, `docs/adr/` was empty. `agentic-setup/templates/ADR-template.md`
existed with zero users. Writing another document would have been the ninth.

So the tool's job is to make documentation *checkable*, not merely written.

## What "green" is not

The distinction this tool exists to enforce, borrowed from the installed
`proof-before-claim` discipline:

| state | meaning |
|---|---|
| **verified** | ran, **and was observed failing when it should** |
| **green** | ran, passed, **never observed failing** |
| **constructed** | reasoned about, never executed |
| **assumed** | believed, never checked |

`spine-check --claims` alone reports **green**. It does not report verified,
because it cannot honestly claim that. Only `--vacuity`, with a declared
`mutate`, can move a claim to verified — by breaking the thing the claim is
about and showing the verdict flips.

## The honest limit

`spine-check` can prove that a command runs, is not trivially passing, and
notices when its subject is deliberately broken.

It **cannot** prove that a command is the right one for its statement. A claim
backed by a plausible-looking but semantically wrong command passes every
mechanical check. Closing that gap needs a human reading the statement against
the code — see `spec/conformance.md`, which is explicit about where the tool
stops.