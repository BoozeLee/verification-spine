# Conformance — what adopting the spine requires

The short version: **`spine-check` proves a command runs, is not trivially
passing, and notices when its subject is broken. It cannot prove that command
is the right one for its statement.** Everything below is arranged around that
limit, because a checker whose boundary is unclear is worse than no checker.

## The three rules

| # | Rule | Checked by | Cost |
|---|---|---|---|
| **R1** | Every claim names a `verify` command a third party can run. | `--claims` | seconds |
| **R2** | Every `verify` executes; a skip is visible, and fatal under `--ci`. | `--ci` | minutes |
| **R3** | Every binding decision has an ADR **with a `## Verification` section naming its enforcement**. | `--adrs` | seconds |

R3 is lifted verbatim from the global `AGENTS.md`: *"an ADR without a
`## Verification` section naming its enforcement is documentation, not a
constraint."* The spine makes a house rule enforceable.

## Adoption order

1. **Your suite must be green first.** No repo adopts the spine on a red suite.
   A gate that gates nothing is the failure mode, not the fix. If a repo is red,
   fixing the first failing test *is* your first claim.
2. Add `spine.manifest.json` at the repo root.
3. Add `docs/adr/` — at minimum one ADR with a real `## Verification` section.
4. Wire `spine-check . --claims --adrs --ci` into CI.
5. *Optional, and the valuable part:* add `mutate` to a claim and run
   `--vacuity`.

## Manifest

```json
{
  "project": "my-project",
  "spine_version": 1,
  "claims": [
    {
      "id": "kebab-case-identifier",
      "statement": "A sentence a reasonable person could disagree with.",
      "verify": "./verify.sh",
      "mutate": "./mutate.sh",
      "expect": "exit 0",
      "timeout": 300,
      "evidence": "docs/evidence/whatever.json",
      "adrs": ["0001"]
    }
  ]
}
```

JSON, not YAML — see `docs/adr/ADR-0001-manifest-is-json-not-yaml.md`.

### Rules `verify` must obey

- **No shell composition.** `./verify.sh && pytest` is rejected outright, not
  silently reinterpreted. `shlex.split` turns it into three argv entries, the
  script ignores two of them and exits 0, and the claim reads as proven when it
  would fail in any real shell. Put the logic in a committed script instead.
- **It must fail when the claim is false.** That is the whole point.
- **Match what CI actually runs.** If your CI invokes `python3 tests/test_all.py`,
  do not write `pytest`. A spine that checks a different command than CI runs is
  checking the wrong thing.

## `mutate` and flip-rate

A claim may declare `mutate`: a command that **breaks the thing the claim is
about**. Then:

1. run `verify` → must PASS
2. run `mutate`
3. run `verify` again → **must now FAIL**
4. restore

The result is reported as `flip-rate n/N`.

| flip-rate | state | meaning |
|---|---|---|
| `1/1` | `VERIFIED` | the evidence is coupled to the claim |
| `0/1` | `VACUOUS` | it passed anyway — the claim proves nothing |
| `0/1` | `UNPROVABLE` | `mutate` changed nothing, so nothing was perturbed |
| — | `GREEN` | no `mutate` declared; never seen to fail |

### The equivalent-mutant trap — read this before trusting a VACUOUS verdict

A `mutate` that breaks something semantically irrelevant leaves `verify`
correctly passing. A naive checker calls that claim vacuous. **That is a false
accusation**, and it is worse than a false green, because it teaches people to
ignore the tool.

So the mutate-effect proof is mandatory. `spine-check` fingerprints the working
tree before and after `mutate`; if nothing changed, the verdict is `UNPROVABLE`,
never `VACUOUS`. When you do get a `VACUOUS`, confirm by hand that your mutation
actually targeted the claim's subject before treating it as a real finding.

Mutation testing cannot be **required** of a repo for this reason: some claims
genuinely have no meaningful mutation, and forcing one manufactures false
findings faster than it finds real ones.

### Following this? Read [`ADOPTING.md`](ADOPTING.md)

This file is the *reference* — what the rules are. `ADOPTING.md` is the
*procedure* — a complete, copy-pasteable walkthrough of adopting on a real
repository, with a full manifest, a full `verify.sh`, a full `mutate.sh`, the CI
block, and a verdict→action table. This document alone is not enough to adopt
from; jev scored it 0.58 for exactly that reason.

## What this tool does not check

Stated plainly, because a checker whose boundary is undocumented will be
trusted past it:

- **Whether `verify` is the semantically right command for its statement.** A
  plausible-looking command that proves the wrong thing passes everything here.
- **Whether `evidence` files are current.** The field is parsed and ignored.
- **Whether a claim is worth making.** It checks the arrow, not the target.
- **Prose in READMEs and docs.** Numbers there decay; nothing here compares them
  against live sources.
- **Cross-repo claims.** `verify` runs with the repo root as cwd and nothing
  else.

Closing the first of those needs a human reading the statement against the code.
That is the honest ceiling.

## Exit codes

| code | meaning |
|---|---|
| `0` | every enabled check passed |
| `1` | a claim failed or timed out; was skipped under `--ci`; or is `VACUOUS`/`DENIED` |
| `2` | manifest unusable, or `--adrs` found a violation |

In CI: treat non-zero as red, and treat a `VACUOUS` finding as something to
investigate rather than something to suppress.