# Design — Verification Spine

**Date:** 2026-10-07
**Status:** conversation-approved · **jev review round 2 = NOT APPROVED (0.89; thesis-calibration 0.44 against)** · not advanced to planning
**Author:** mcode session `mvs_781569c6723f4a7c82df3d63784b883b`
**Scope:** a longer product/portfolio track. **Does not begin before 2026-10-13** (screening).

---

## 1. Vision

> **Every claim carries re-runnable evidence.**

A *claim* is a sentence a reasonable person could disagree with. Its *evidence* is a
command that passes or fails, runnable by someone who does not trust the author.

This is the portfolio's product. The individual repositories are applications of it,
not competing entries in a list of things that were built.

### Why this framing, and not "agent tooling"

The scout ranking put six unrelated-looking tools near the top. Counting
verification/evidence vocabulary in each README shows they are not unrelated:

| project | verification-word hits in README |
|---|---|
| `hirebridge` | 41 |
| `elohim` | 13 |
| `verification-skills` | 12 |
| `harness` | 8 |
| `vectorforge` | 7 |
| `awesome-mcode` | 6 |

`harness` gates agent readiness. `elohim` gates numerical claims by residual.
`mcp-regression-lab` gates MCP contracts by diff. `hirebridge` gates hiring claims by
re-running their proof commands. `galacticfederation`/RepoTruth gates a repository's
self-description against its actual contents. Same primitive, five surfaces.

**Status of this thesis: provisional.** jev-1.13.0 scored "are these genuinely one idea?"
at **0.71** (§12) — prior, not decided. It is a strong reading of the evidence, not a
settled fact, and Wave 1 exists to test it on one repository rather than assume it across
eight. What the evidence does *not* yet show: that these repos are the right set, that
the grouping helps a user, or that anyone wants a spine at all.

---

## 2. Problem statement (evidence)

All measurements below were taken on 2026-10-07 and are reproducible.

**P1 — Decisions have no recorded rationale.** Across the eight top projects,
`docs/adr/` is **empty in every one** (0 ADRs). Meanwhile `~/agentic-setup/templates/ADR-template.md`
exists with zero users.

**P2 — This failure mode has already happened and been documented.** `agentic-setup/ROADMAP.md`,
Phase 1, records it verbatim: *"S7 wrote a plan from the ledger and jev ranking, never checked
`docs/adr/`, built three worktrees, then reverted against ADR-0022 and ADR-0025."* The
diagnosis exists; the fix never landed.

**P3 — Docs without enforcement do not survive here.** `agentic-setup/` already contains
`ROADMAP.md`, `META-ARTIFACTS.md`, `DELIVERY-STANDARD.md` and six templates. None of them
changed behaviour. The next document will not either.

**P4 — Infrastructure is already duplicated.** `~/workspace/foundation-ai-engine/` contains
only `dependencies/` (9 vendored repos) and no source, docs, or git history. It is an
abandoned alternative to `agentic-setup`. A second foundation would compound this.

**P5 — Green is not yet trustworthy in one flagship repo.** `mcp-regression-lab` has 3 of
123 tests failing, two of them SSRF guards
(`guardedFetch refuses a hostname that resolves to loopback`,
`a redirect to a loopback IP literal is refused`). The project whose premise is
"catches regressions quietly" has a broken loopback guard.

---

## 3. The spine contract

A repository joins the spine by declaring its claims in `spine.manifest.yaml` at its root.

```yaml
project: elohim
spine_version: 1
claims:
  - id: residual-gate-holds
    statement: "A numerical claim is only a finding after its residual is measured"
    verify: "uv run --frozen pytest -q tests/test_residual.py"
    expect: "exit 0"
    evidence: "docs/evidence/residual-gate.json"
    adrs: ["0001"]
```

### Three rules, each mechanically checkable

| # | Rule | Checked by |
|---|---|---|
| **R1** | Every claim names a `verify` command a third party can run. | `spine-check` schema validation |
| **R2** | Every `verify` executes in CI and is not silently skipped. | `spine-check --ci` |
| **R3** | Every binding decision has an ADR **with a `## Verification` section naming its enforcement**. | `spine-check --adrs` |

**R3 is not invented here.** It is lifted from the existing global `AGENTS.md`:
*"An ADR without a `## Verification` section naming its enforcement is documentation,
not a constraint."* The spine makes an existing house rule enforceable.

### Claim schema

| field | required | meaning |
|---|---|---|
| `id` | yes | stable slug, unique in the repo, never reused |
| `statement` | yes | the falsifiable sentence |
| `verify` | yes | shell command; exit code is the verdict |
| `expect` | yes | `exit 0` (v1 supports only this) |
| `evidence` | no | path to a recorded artifact; absence is allowed, presence is better |
| `adrs` | no | ADRs that constrain this claim |

---

## 4. Architecture

### Five layers, no new governance bodies

| Layer | Home | Role | Status |
|---|---|---|---|
| Product semantics | `~/verification-spine/` (new) | vision, schema, ADR convention, conformance | new |
| Agent process | `~/agentic-setup/` | ownership, repo-lock, session discipline | **existing — role unchanged** |
| Gate execution | `~/harness` | runs gates, `scan --fail-under N` exits 1 | existing, extended |
| Claim primitive | `~/hirebridge` | claim → command → result → tamper suite | existing |
| Applications | the project repos | each adopts `spine.manifest.yaml` + `docs/adr/` | migrated |

The spine owns *what the product means*. `agentic-setup` owns *how the agent works*.
`harness` *executes* gates. These do not overlap, and the spine does not absorb
`agentic-setup`.

### Spine repo layout

```
~/verification-spine/
  VISION.md                         # the one sentence, and why it is true
  spine.manifest.yaml               # the spine's own claims — dogfooding
  spec/
    claim-evidence.schema.yaml
    adr-convention.md
    conformance.md
  bin/
    spine-check                     # the enforcer (Python, stdlib only)
  docs/
    adr/                            # the spine's own ADRs, each with ## Verification
    evidence/
  ROADMAP.md
```

### Per-project layout (adopted later, not now)

```
<repo>/
  spine.manifest.yaml
  docs/adr/NNNN-slug.md             # each with a ## Verification section
  docs/evidence/
```

---

## 5. Enforcement mechanics

`bin/spine-check` is the only new code. Python, stdlib only — matching `harness`, so it
installs with `uv tool install` and needs no runtime.

```
spine-check <repo-path>        # validate manifest, run each verify, report per-claim
spine-check --ci <repo-path>   # fail if any verify was skipped
spine-check --adrs <repo-path> # fail if any ADR lacks ## Verification
spine-check --tamper <repo>    # mutate a claim's evidence; assert the checker notices
```

### Failure semantics

- A `verify` command that **times out** is a failure, never a pass. Default timeout 300s,
  overridable per claim.
- A `verify` that is **skipped** is a failure under `--ci`. Silent skipping is the failure
  mode that makes gates decorative.
- A malformed manifest is a hard error with a line number, never a warning.
- `spine-check` exits non-zero on any violation. It is designed to be a CI gate, so it
  must never exit 0 on partial information.

### Why `harness` runs it rather than a new gate runner

`harness` already scans a repo, scores it, and exits 1 below a threshold. Adding a `spine`
check to it avoids a second gate runner competing for the same job. `harness` stays
generic; it gains one more thing to check.

---

## 6. Migration plan

Ordered by leverage per hour, not by interest — the principle `agentic-setup/ROADMAP.md`
already states and this design inherits.

### Gate rule for the whole migration

**No repository adopts the spine until its own test suite is green.**

A repo with red tests wrapping itself in an evidence contract is theatre. This is not
hypothetical — it is exactly the current state of `mcp-regression-lab`.

### Wave 1 — dogfood (start after 2026-10-13)

Prove the enforcer before trusting it. Three repos, in order:

1. **`elohim`** — 319 passed / 1 skipped. Green. The flagship. Declares claims about the
   residual gate and the sha256 contract.
2. **`mcp-regression-lab`** — **starts with fixing the 3 failing tests**, including both
   SSRF guards. The fix is the first claim the repo declares. Only then does it adopt.
3. **`hirebridge`** — 58 cargo tests green. Already implements claim → evidence →
   tamper suite; adopting the spine is mostly a manifest.

**Waves 2 and 3 are conditional, not scheduled.** Per the jev ruling (§12), week
arriving is not the trigger — two repos actually using `spine-check` is. The wave
numbering is an ordering, not a calendar.

### Wave 2 — extend the engine, then the tooling

4. `harness` gains `spine-check` integration.
5. `verification-skills`, `awesome-mcode` adopt the spec.

### Wave 3 — the remainder

6. `vectorforge` (after its red Ollama integration test is fixed — same gate rule),
   `galacticfederation`, `elohim-web`.

### Not migrated

The 165 HARVEST-verdict repositories from `~/project-scout/projects.json`. Adoption is
opt-in per repo, never a sweep.

---

## 7. What this explicitly does not do

- **No shared runtime library.** Stacks differ (Python, Rust, TypeScript). Cross-imports
  would either fragment or force a visibility merge.
- **No monorepo, no visibility merge.** Public repos (`harness`, `mcp-regression-lab`,
  `elohim`) and private repos (`hirebridge`, `vectorforge`, `awesome-mcode`) stay separate.
- **No absorption of `agentic-setup`.** It keeps ownership, repo-lock and session discipline.
- **No retroactive migration of the 165 HARVEST repos.**
- **No new weekly ceremony, dashboard, or status meeting.**

---

## 8. Risks and mitigations

| # | Risk | Mitigation |
|---|---|---|
| R-1 | The spine becomes the **ninth unused document**. | Kill criterion, decided now: if `spine-check` is not used by **two** repos within **two weeks** of Wave 1 starting, kill the spine and keep the ADRs. |
| R-2 | Enforcement-first is slower than docs-first, and it will feel slower. | Wave 1 deliberately starts with a repo (`elohim`) that is already green, so the first success is cheap. |
| R-3 | `spine-check` itself becomes an unmaintained tool. | It must be adopted by `harness` in Wave 2, or it is dead weight. |
| R-4 | A public repo's manifest leaks the existence of a private repo in the spine. | Manifests reference claim IDs, not repo names, across repo boundaries. Names appear only in the private spine repo. |
| R-5 | **This competes with the screening for the same hours.** | Migration does not start before 2026-10-13. Enforced in `NEXT_7_DAYS.md`, not just intended here. |
| R-6 | `foundation-ai-engine/` stays as a second, ambiguous foundation. | Decide its fate in Wave 1: either delete the empty shell or explicitly mark it archived. Not left ambiguous. |

---

## 9. Testing strategy

The spine's own correctness is tested by attacking it.

| test | method | passes when |
|---|---|---|
| **Manifest validation** | unit tests over schema cases | malformed manifests fail with a line number |
| **Honest repo passes** | run against `elohim` | exits 0 |
| **Ineligible repo fails** | run against `mcp-regression-lab` pre-fix | exits non-zero on red tests |
| **Skip detection** | claim marked skipped, run with `--ci` | exits non-zero |
| **ADR rule** | ADR without `## Verification` | exits non-zero |
| **Anti-decorative (critical)** | break a claim's evidence, re-run | **the checker notices** |
| **Timeout is failure** | claim whose verify sleeps forever | exits non-zero after the timeout |

The anti-decorative test is the one that matters. If tampering a claim changes nothing,
the spine is fiction — and this test is the only thing that would catch that.

---

## 10. Success criteria

The track succeeds when all of these hold:

1. `spine-check` exits 0 across the three Wave-1 repositories.
2. Each declares ≥1 real claim whose `verify` actually executes in CI.
3. Every binding decision in those repos has an ADR with a `## Verification` section.
4. The anti-decorative test passes: tampering a claim's evidence is caught.
5. `harness` runs `spine-check` without a bespoke runner.
6. `foundation-ai-engine/` has an explicit, recorded fate.

**The floor, if the spine is killed.** Criterion 1–3 are the floor and survive the §8 R-1
kill: every adopted repo keeps its ADRs, its claim manifest, and a gate that runs. If
`spine-check` dies with the spine, those repos are strictly better off than before the
track started. A track that can only succeed by never failing was mis-scoped.

Explicitly **not** a success criterion: a large documentation corpus, a dashboard, or a
count of ADRs. Volume is not the goal; enforcement is.

---

## 11. Open questions

| # | Question | Blocks | Resolution |
|---|---|---|---|
| Q1 | Should `spine-check` live inside `harness` outright, or as a separate package it invokes? | Wave 2 step 4 | Lean: separate package, invoked by `harness`. Keeps `spine-check` testable without `harness`, and keeps the AGPL/Apache licensing boundary clean — `harness` is AGPL-3.0, `hirebridge` is MIT. |
| Q2 | Should the spine require `evidence` artifacts, or is the `verify` command enough? | v1 schema | v1: command is required, artifact optional. Enforcing artifacts doubles the work before any repo is adopted. Revisit once three repos have run. |
| Q3 | Does `verification-skills` itself become the spec's implementation, or does it stay documentation? | Wave 2 step 5 | Lean: documentation + examples, not the enforcer. One enforcer, or none is trustworthy. |

---

## 12. Decision record — jev-1.13.0

The spec was reviewed by `jev` (CLI 0.6.2, model jev-1.13.0) on 2026-10-07 against the
standing rule in `ops-2026-10-04/jev-decisions.md`: **≥0.9 act as decided · <0.5 prior
against, no action · 0.5–0.9 prior, acted on only when the action is reversible.**

| # | question | score | ruling |
|---|---|---|---|
| q3 | Start Wave 1 after the 2026-10-13 screening? | **0.95 conf / 0.97 prob** | **DECIDED** — `after_screening`. Spec §6 already complies. |
| q4 | Which repo pilots the spine first? | **0.85 / 0.89 → elohim** | Prior, decisive (0.89 vs 0.08/0.02/0.01). Spec §6 already complies. |
| q2 | Enforcement before documentation? | 0.76 | Prior — supports §5 as written. |
| q1 | Are the 8 repos genuinely one idea? | **0.71** | **Prior — the weakest affirmative.** |
| q5 | Refuse a shared runtime library? | 0.69 | Prior — supports §7 as written. |
| q6 | Is the 2-repo/2-week kill criterion fair? | **0.63** | Prior, weak. |

### What this ruling changes

**Nothing was confirmed as a clean approval, and the thesis did not clear 0.9.** Two
decisions firmed (timing, first adopter) already matched the spec, so they stand
unchanged. The three "prior" answers — including the central thesis at 0.71 — are treated
as a constraint, not a mandate:

1. **The thesis is provisional, not settled.** §1 states what the evidence supports and
   what it does not. Wave 1 tests the thesis on one repo. It is not assumed across 8.
2. **The floor is the per-repo ADRs, not the spine.** If the spine is killed under the
   §8 R-1 criterion, each adopted repo keeps its ADRs, its claim manifest, and its working
   gate. Nothing rolls back. This is what makes the track reversible at 0.71 confidence.
3. **Waves 2 and 3 are conditional on Wave 1 evidencing itself**, not scheduled. Wave 2
   does not begin because week 2 arrived; it begins because two repos are using
   `spine-check`. §6's wave numbering is an ordering, not a calendar.

### Round 2 — after applying the changes above

| # | question | score | ruling |
|---|---|---|---|
| q1 | Ready to become the basis of an implementation plan? | **0.89** | Prior — **below the 0.9 threshold, so not approved** |
| q2 | Is the thesis now stated with appropriate epistemic humility? | **0.44** | **PRIOR AGAINST — "no action"** |
| q3 | Single-repo Wave 1, or 2–3 repos at once? | 0.71 | Prior — single repo is the better bet |
| q4 | Does the FLOOR clause genuinely de-risk the track? | 0.70 | Prior — mildly, not decisively |

**Status: NOT APPROVED. The spec has not advanced to planning.**

jev answered round 1's weakest item the same way twice. The 0.44 on q2 is the important
one: hedging the *consequences* of a wrong thesis (the reversibility floor) does not fix a
thesis that is still *stated* too strongly. Round 2 changed what happens if the spine
fails; it did not change what the spec claims the spine *is*.

**What that critique points at, honestly.** The thesis rests on README keyword counts
(`hirebridge` 41, `elohim` 13, `verification-skills` 12, `harness` 8 …). A lexical overlap
is weak evidence that eight repositories are one product. It is real evidence that they
share *vocabulary*; it is not evidence that a user wants them unified, that the set is
the right eight, or that a spine adds anything over each project simply writing its own
ADR. The spec currently builds five layers of architecture on top of that.

**The available fix** is structural, not cosmetic: demote the thesis from *the product* to
*a hypothesis under test*. The spine stops being a standard eight repos must satisfy and
becomes an experiment run on one repository, with the per-repo ADRs — which are already
the thing `agentic-setup` failed to land — as the deliverable that survives regardless.
That change is not cosmetic relabelling; it removes the architecture that the weak
evidence was carrying.

Re-submitting for a third round was not done automatically. Two rounds have been spent,
the second round's score moved on the *consequences* but not the *claim*, and tuning
prompts until a number crosses a threshold would be fitting to noise. The decision to
either restructure the thesis or drop it is the owner's, not the loop's.

The kill criterion (§8 R-1) is retained rather than loosened. jev scored it 0.63, which
is a weak endorsement of a weak gate — not grounds for removing the only mechanism that
stops this becoming a ninth unused document. If the criterion proves wrong, the correct
response is to measure Wave 1 and amend it with data, not to delete it before it has ever
fired.

---

## 13. Provenance

Findings in §2 come from `~/project-scout/REPORT.md` and `projects.json` (2026-10-07 scan
of 170 projects) plus direct inspection of `~/agentic-setup/ROADMAP.md`,
`~/.minimax/config.yaml`, and the eight top repositories. Claim states follow the global
`AGENTS.md` convention: **verified** = a command was run and its output is cited;
**constructed** = reasoned from rules but not executed.