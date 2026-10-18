# Execution evidence

**This file owns observed results.** It records what was *measured*, not what was
intended. `PLANS.md` decides status; this file is why that decision is defensible.

Append as evidence appears, **not** at end of session. Five of thirteen sessions on
2026-10-04 ended `aborted` while a build was still live; anything written only at
the end died with them.

## Rules for this file

- Record the **command** and its **observed output**, not a summary of intent.
- Never copy private conversations, credentials, or complete command logs.
- Write limits plainly. "Local verification is not a hosted CI run" is the sentence
  that stops the next session claiming something this file never proved.
- A gate you did not observe failing is not a passing gate. Say so.

---

## 004 — 2026-10-07 15:20–16:20 CEST

**Task:** Close the three governance gaps and make the repository self-describing.

No `harness/build/` plan file: the work is mechanical and was fully specified by
the `session-close.sh` FAIL output.

### Commands run and observed results

| Command | Exit | Observed |
|---|---|---|
| `python3 -m pytest -q` | `0` | `90 passed in 7.96s` |
| `bash bin/self-check.sh` | `0` | `spine-check accepts the conformant repo and rejects all four broken ones` |
| `bash bin/check-closing-adr.sh` | `0` | `ADR-0002 records the ruling, its scores, and its own verification` |
| `./bin/spine-check . --adrs` | `0` | `spine-check: OK` |
| `gitleaks detect --source . --redact` | `0` | `no leaks found` (18 commits, ~159 KB) |
| `sha256sum LICENSE` | `0` | `0d96a4ff68ad6d4b6f1f30f713b18d5184912ba8dd389f86aa7710db079abcb0`, 34,523 bytes |
| `git rev-parse HEAD` vs `git ls-remote origin HEAD` | `0` | identical `7496198`; `rev-list --left-right --count` → `0  0` |
| `bash agentic-setup/scripts/session-close.sh .` | `1`→`0` | `2 passed · 5 failed` → `7 passed · 0 failed` |

ADR rename, verified in place:

| Command | Exit | Observed |
|---|---|---|
| `bash bin/check-closing-adr.sh` after rename | `0` | still passes — its hardcoded path was updated with the file |
| `./bin/spine-check . --adrs` after rename | `0` | `spine-check: OK` — R3 parses `ADR-*.md` and `NNNN-*.md` alike (`src/spine_check/adrs.py:91`) |

### Red-proofs

Fault injected, gate re-run, gate reverted. A gate never observed failing is not
evidence — see `AGENTS.md` §5.

| Gate | Injected fault | Exit (expect non-zero) | Reverted |
|---|---|---|---|
| `bin/self-check.sh` | dropped `--vacuity` from step 4 | `1` — `SELF-CHECK FAILED` | yes |
| `bin/self-check.sh` (pre-fix, same fault) | same | **`0` — false green, reproduced** | n/a |

The second row is the point. The pre-fix script never ran `spine-check` for step 4
at all, so it could not observe a failure. Both fault copies were moved to trash;
neither touched the tracked tree.

### What was actually broken

`bin/self-check.sh` resolved `CHECK` as a relative `./bin/spine-check`, then step 4
`cd`'d to `/tmp/spine-selfcheck` and invoked it there. The binary is not in that
directory, so the call exited `127`. Because every rejection test is written
`cmd && fail "..."`, a missing executable takes the same branch as a correct
rejection. Step 4 — "a `true`-backed claim must be denied" — was therefore
**vacuous**: it would have stayed green if the `DENIED` behaviour were deleted
outright.

The behaviour itself was never wrong. `tests/test_vacuity.py:147` covers it, and
running the command by hand gives `vacuity t: DENIED`, exit 1.

### Limits

- Not verified: that any of this is enforced on a **hosted** runner. Every result
  above is local. `.github/workflows/spine-check.yml` exists but has never executed
  on GitHub — the repository had no remote until today.
- Not verified: `session-close.sh` on `elohim`. Its CI blocker is recorded in
  `PLANS.md`; the spine cannot currently be installed by elohim's CI at all.
- The `docs/superpowers/specs/` and `plans/` files still reference the pre-rename
  `0001-manifest-is-json.md`. They are historical planning records and were
  deliberately left unedited rather than rewritten after the fact.

### Rollback

`git revert` the single commit. The rename is reversible with `git mv` back to the
old names plus the three reference edits; nothing outside this repository reads
those paths.

---

## 003 — 2026-10-07 (cross-repo, recorded here on purpose)

**Task:** None. This is a gate-integrity note that does not belong to any one repo.

`mcp-regression-lab` was recorded for days as shipping **3 failing tests**, two of
them SSRF guards, and `fix_ssrf` was ruled at 0.68/0.76. Every one of those numbers
was wrong.

Its gate is `"test": "node --test 'test/*.test.ts'"` with `engines: node >=24`. The
failing runs came from `bun test`, which ignores that script and executes under
Bun's runtime, where the undici `dispatcher` carrying the `safeLookup` hook is
silently dropped. The SSRF guard never ran; the request went to `https://localhost/mcp`
and died `ConnectionRefused`, which the assertion read as "the guard missed it".

| Command | Exit | Observed |
|---|---|---|
| `bun test` (wrong runner) | `1` | `120 pass · 3 fail` — both SSRF guards "failing" |
| `npm test` (the project's own gate) | `0` | `tests 123 · pass 123 · fail 0` |

Acting on the wrong measurement would have meant loosening a working SSRF guard to
satisfy a runner the project does not use. **Read the gate before believing a
failure.** `mcp-regression-lab` was not modified; `fd --changed-after 2026-10-07`
returns zero files.

---

## 001–002 — 2026-10-07 (wave 1)

**Task:** Build `spine-check` (tasks 1–5) and adopt it on `elohim` (task 6).

Plan: [docs/superpowers/plans/2026-10-07-verification-spine-wave1.md](docs/superpowers/plans/2026-10-07-verification-spine-wave1.md).

| Command | Exit | Observed |
|---|---|---|
| `python3 -m pytest -q` | `0` | `90 passed in 8.02s` |
| `bash bin/self-check.sh` | `0` | conformant fixture accepted, four broken fixtures rejected |
| bundle restore drill: clone `verification-spine-2026-10-07.bundle` → test | `0` | 19 commits recovered, `90 passed in 8.01s` |
| `cd ~/Bakery-street-project/elohim && python3 tests/test_all.py` | `0` | `ALL_SKILLS_PASS` |
| `spine-check` tamper proof on the real `elohim` repo | `1`→`0` | broken claim → exit 1; reverted → exit 0 |

Three bugs were found by running the tool against itself. They are recorded in
[ROADMAP.md](../ROADMAP.md) because each one is a different way for a verification
gate to lie: a claim that fails in any real shell reported PASS; the command a user
actually types was unrunnable while all 40 tests passed; and a mutation outlived
its run because restore used `git checkout`, which does nothing for untracked files.

### Limits

- The symlink hardening was **not** done (jev 0.16, below the action threshold, then
  overridden by the user). Recorded as a chosen state in ADR-0002.
- `bundle restore` is a local-disk drill. No copy of this repository has ever left
  the machine under anything other than today's push.
---

## 005 — 2026-10-17 (release engineering, branch `release/v0.1.0`)

**Task:** ship 0.1.0 per `spec/release-v0.1.0.md` and ADR-0003. Release-only scope; ADR-0002 stands.

### Baseline on `master` (before any change)

| Command | Exit | Observed |
|---|---|---|
| `pytest -q` | `0` | `90 passed in 7.87s` |
| `./bin/spine-check . --claims --adrs --ci` | `0` | 3 claims PASS, `spine-check: OK` |
| `gitleaks detect --source . --redact` | `0` | `no leaks found` (206 KB scanned) |

### After the release claim landed

| Command | Exit | Observed |
|---|---|---|
| `./bin/spine-check . --claims --adrs --ci` | `0` | 4 claims PASS — including `release-artifact-installs-and-behaves` (first run: **FAIL**, see finding below) |
| `./bin/spine-check . --vacuity --claims` | `0` | release claim `VERIFIED flip-rate 1/1`; mutation corrupted `pyproject.toml`, build failed, verdict flipped, tree restored byte-identical |
| `pytest -q` | `0` | `90 passed in 7.87s` |
| `gitleaks detect --source . --redact` | `0` | `no leaks found` |
| `uvx semgrep scan --config p/python --quiet --error .` | `0` | no findings (local `~/.local/bin/semgrep` is an orphaned pipx shim; its venv is gone) |

### Finding: the first version of the release claim was wrong, and the gate said so

`bin/release-check.sh` originally used `tests/fixtures/repo_tamper` as its
negative control without planting a defect. `repo_tamper` is **conformant by
default** — its claim passes until a tamper test breaks it on purpose — so the
installed wheel correctly accepted it and the claim read `FAIL (exit 1)`.
The checker was right; the claim's evidence was wrong. Fixed by using
`repo_fail` (failing claim) and `repo_bad_adrs` (unenforced ADR) as the
negative controls. This is the tool catching its own release path — recorded
rather than smoothed over.

### Limits

- Local verification only. Neither workflow has executed on a hosted runner;
  `release.yml` is verifiable only after the approved push and tag.
- Commits are staged but unsigned so far: `commit.gpgsign=true` with an SSH
  key whose passphrase is not available to this agent shell (no identities in
  the session agent). Signing happens once the key is loaded in the user's
  session (`ssh-add ~/.ssh/id_ed25519`).

### Rollback

`git checkout master && git branch -D release/v0.1.0` — everything lives on the
branch; `master` is untouched.

### Hosted verification (closing the Limits above) — 2026-10-18

| run | trigger | result | observed |
|---|---|---|---|
| `release.yml` on tag `v0.1.0` | tag push | **success** | release `v0.1.0` published, not draft, assets `spine_check-0.1.0-py3-none-any.whl` (26,868 B) + `spine_check-0.1.0.tar.gz` (74,072 B) |
| `spine-check.yml` on `master` | push | **success ×3** | py 3.10 / 3.12 / 3.13 each green (~25s): suite, tamper negative control, self-check incl. the release claim — first hosted execution of this workflow ever |

Two facts worth keeping:

- The first CI attempt failed in 3s with **"job was not started because recent
  account payments have failed or your spending limit needs to be increased"**
  — it fired while the repository was still private (billed minutes). The
  release run that followed succeeded because the repo had just gone public
  (free minutes). A CI failure with zero steps executed is a billing signal,
  not a code signal.
- The review before push found the workflow triggered on `branches: [main]`
  while the default branch is `master` — CI could never have run on a push.
  Fixed in `d27cb63`. Known cosmetic warning: both pinned actions target
  Node 20 and are force-upgraded to Node 24 by GitHub.
