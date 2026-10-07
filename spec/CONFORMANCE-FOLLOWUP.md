# Plan — conformance follow-up

**Date:** 2026-10-07
**Driver:** jev-1.13.0 ruling on `spec/conformance.md`, same day
**Standing rule:** ≥0.9 act as decided · <0.5 prior against, no action · 0.5–0.9 prior, reversible only

## The ruling

| # | question | score | ruling |
|---|---|---|---|
| q2 | Are the limits stated honestly? | **0.75** | prior — candid, not marketing |
| q3 | Keep building, or stop and keep only the ADRs? | 0.61 | prior, weakly keep |
| q1 | Is the adoption guide sufficient for an independent engineer? | **0.58** | **prior — weakest. Critical steps are implicit.** |
| q4 | Worth having existed if only `elohim` adopts it? | **0.50** | **borderline. No clear yes.** |
| q5 | Is the 2-repo / 2-week kill criterion right? | **0.36** | **PRIOR AGAINST — no action.** |

Three of five landed below 0.6. This is not a document that is nearly right; it is
a document that has not earned the authority it asks adopters to give it.

## What the ruling changes

### 1. The kill criterion is withdrawn — *acted on, decided against*

`q5 = 0.36` is below the 0.5 threshold, so under the standing rule it takes **no
action**: the criterion comes out. It has now been scored 0.63 and 0.36 in two
separate rounds, and defending a mechanism twice against a below-threshold
verdict is not maintaining a safeguard, it is keeping a rule nobody believes.

It is removed from `ROADMAP.md` and `spec/conformance.md`. What replaces it is
not a better deadline — it is a **decision rule** tied to observable use rather
than elapsed time, below.

### 2. The adoption guide is rewritten, not patched — *the actual work*

`q1 = 0.58` says an independent engineer cannot adopt correctly from what is
there. Concretely, what is missing today:

- **No worked example.** Four abstract JSON snippets, none complete. An adopter
  must invent the `verify.sh`, decide what belongs in a `mutate.sh`, and guess
  the CI wiring.
- **No copy-paste CI block.** "Wire the CLI into CI" is not a step.
- **No failure-to-fix table.** When `spine-check` exits 1, the doc says treat it
  as red. It does not say *what each verdict means and what to do about it*.
- **No ordering guarantee stated.** It lists five steps but never says which are
  mandatory versus valuable, so a reader can skip step 1 and adopt on a red
  suite — the exact thing the gate rule exists to prevent.
- **No worked `mutate`.** `mutate` is the most valuable and least obvious
  feature, and it is described in one sentence.

Deliverable: `spec/ADOPTING.md` — a single end-to-end walkthrough of adopting on
a real repository, with a complete manifest, a complete `verify.sh`, a complete
`mutate.sh`, a copy-paste CI block, and a verdict→action table. `conformance.md`
becomes the *reference* (what the rules are); `ADOPTING.md` becomes the
*procedure* (how to comply). One document cannot be both and stay short.

### 3. `q4 = 0.50` reframes the priority order — *acted on*

Wave-1 value was a coin flip, which means the spine's value does not rest on the
tool being widely adopted. So the highest-value item is no longer "adopt on more
repos" — it is the **five-minute edit** to `agentic-setup/templates/ADR-template.md`
that unblocks every adopter at once, and the `elohim` adoption as the single
reference implementation that proves the guide works.

`ROADMAP.md` reorders accordingly. Wave 2 (`harness` integration) drops to
explicitly optional; teaching the gate runner to call a tool with one adopter is
premature.

### 4. `q2 = 0.75` — leave the limits alone

The candid section is the most-valued part of the document. It is not softened,
shortened, or moved to a footnote.

## Decision rule replacing the kill criterion

> The spine survives while a claim it certifies is still being read by someone
> other than its author. It ends when no repo outside this one runs it, or when
> its author stops believing it — whichever comes first. There is no deadline,
> because a deadline rewards adoption that nobody needed.

Reversible by construction: ending the spine keeps every ADR, every manifest and
every gate. Nothing rolls back.

## Execution order

1. Write `spec/ADOPTING.md` — the walkthrough. **This is the whole point of the
   ruling.** Gate: an engineer who has never seen the tool follows it end to end
   and ends with a green CI run.
2. Add a test that walks `ADOPTING.md`'s example end to end, so the guide cannot
   rot against the code. Gate: `ADOPTING.md` is executable.
3. Remove the kill criterion from `ROADMAP.md` and `conformance.md`; insert the
   decision rule.
4. Fix `agentic-setup/templates/ADR-template.md` — add `## Verification`. Gate:
   an ADR written from the template passes `spine-check --adrs`.
5. After 2026-10-13: adopt on `elohim` as the reference implementation.
6. Re-run jev on the revised `conformance.md` + `ADOPTING.md`.

## Not doing

- Not softening the limits section (0.75, the best-scoring answer).
- Not widening the tool's scope to close the semantic gap. That gap is real,
  stated honestly, and closing it needs a human reading code — not a heuristic.
- Not starting Wave 2. `q4 = 0.50` does not support building more before one
  external adopter exists.