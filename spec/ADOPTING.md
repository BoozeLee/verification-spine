# ADOPTING — a complete walkthrough

Copy-paste this. It takes about twenty minutes on a repository whose test suite
is already green.

`conformance.md` is the reference — *what the rules are*. This file is the
procedure — *how to comply*. Everything here is executable; `tests/test_adopting.py`
runs it, so it cannot rot against the code.

---

## Before you start: the gate rule

**Your test suite must be green first.** A repository with failing tests wrapping
itself in an evidence contract is theatre, not verification.

If your suite is red, fixing the first failure *is* your first claim. Do not
start here until the suite passes.

```bash
# Whatever your CI actually runs. Note the exact command — step 5 needs it.
<your test command>
```

---

## 1. Install the checker

No dependencies, no network. Clone it beside your repo:

```bash
git clone <verification-spine-url> ~/tools/verification-spine
~/tools/verification-spine/bin/spine-check --help
```

It resolves its own path, so it works from any directory without `PYTHONPATH`.

---

## 2. Write the manifest

Create `spine.manifest.json` at your repository root:

```json
{
  "project": "my-project",
  "spine_version": 1,
  "claims": [
    {
      "id": "my-test-suite-passes",
      "statement": "Every test in this repository passes.",
      "verify": "./spine-verify.sh",
      "expect": "exit 0",
      "adrs": ["0001"]
    }
  ]
}
```

| field | required | notes |
|---|---|---|
| `id` | yes | kebab-case, unique, never reused |
| `statement` | yes | a sentence a reasonable person could disagree with |
| `verify` | yes | argv, **not** a shell string — see the warning below |
| `mutate` | no | see §5 |
| `expect` | yes | only `"exit 0"` is defined in v1 |
| `timeout` | no | seconds, default 300 |
| `evidence` | no | path to a recorded artefact; parsed but not enforced |
| `adrs` | no | ADR ids this claim is bound to |

> **`verify` is argv, not shell.** `./verify.sh && pytest` is **rejected**, not
> reinterpreted. `shlex.split` would turn it into three argv entries, the script
> would ignore two of them and exit 0, and the claim would read as proven when it
> fails in any real shell. Put the logic in a committed script.

---

## 3. Write `verify.sh`

```bash
#!/bin/sh
# Must exit 0 while the claim holds, non-zero when it stops holding.
set -e
exec <your exact test command>
```

```bash
chmod +x spine-verify.sh
```

**Use the command your CI runs.** If CI invokes `python3 tests/test_all.py`, do
not write `pytest`. A spine that checks a different command than CI runs is
checking the wrong thing — and it will stay green while CI is red.

---

## 4. Write the ADR

Copy `templates/ADR-template.md` from `agentic-setup`. Fill in Context,
Decision, and **Verification** — the last one names the command that would fail
if the decision stopped being true.

Save it as `docs/adr/ADR-0001-<slug>.md`. Both `ADR-0001-slug.md` and
`0001-slug.md` are recognised, so either works.

An ADR without `## Verification` fails. That is the rule from your global
`AGENTS.md`, now enforced rather than aspirational.

---

## 5. Check it, honestly

```bash
~/tools/verification-spine/bin/spine-check . --claims --adrs --ci
```

`exit 0` means every claim passed and nothing was skipped.

**Confirm it can fail.** A check that has only ever passed is *green*, not
*verified*. Break something and watch it go red:

```bash
# deliberately break your verify script
printf '#!/bin/sh\nexit 1\n' > spine-verify.sh
~/tools/verification-spine/bin/spine-check . --claims --ci   # must exit 1
git checkout -- spine-verify.sh                             # or restore by hand
~/tools/verification-spine/bin/spine-check . --claims --ci   # must exit 0 again
```

If it does not go red, your claim is not coupled to anything. Fix that before
going further.

---

## 6. Wire it into CI

```yaml
      - name: Spine
        run: ~/tools/verification-spine/bin/spine-check . --claims --adrs --ci
```

Add a negative control while you are there — a gate nobody has watched fail is
green, not verified:

```yaml
      - name: Negative control — tamper a claim, confirm the checker objects
        run: |
          set -e
          cp spine-verify.sh /tmp/verify.bak
          trap 'cp /tmp/verify.bak spine-verify.sh' EXIT
          printf '#!/bin/sh\nexit 1\n' > spine-verify.sh
          if ~/tools/verification-spine/bin/spine-check . --claims --ci; then
            echo "::error::checker passed a deliberately broken claim"
            exit 1
          fi
```

---

## 7. Make it `VERIFIED` — the valuable part

Steps 2–6 get you to **GREEN**: your claim passes and has never been seen to
fail. To move it to **VERIFIED**, declare a `mutate` — a command that breaks the
thing your claim is about:

```json
"mutate": "./spine-mutate.sh"
```

```bash
#!/bin/sh
# Break exactly what the claim is about.
# Restore is handled automatically from a snapshot.
set -e
sed -i 's/<the thing your claim asserts>/BROKEN/' path/to/source.py
```

Then:

```bash
~/tools/verification-spine/bin/spine-check . --claims --vacuity
```

| flip-rate | state | what it means |
|---|---|---|
| `1/1` | `VERIFIED` | the evidence is coupled to the claim |
| `0/1` | `VACUOUS` | it passed anyway — the claim proves nothing |
| `0/1` | `UNPROVABLE` | `mutate` changed nothing; vacuity cannot be concluded |
| — | `GREEN` | no `mutate` declared |

### Read a `VACUOUS` verdict carefully

A `mutate` that breaks something semantically irrelevant leaves `verify`
correctly passing. A naive checker calls that claim vacuous — and **a false
accusation is worse than a false green**, because it teaches people to ignore the
tool.

So `spine-check` fingerprints the working tree before and after `mutate`. If
nothing changed you get `UNPROVABLE`, never `VACUOUS`. When you do get a
`VACUOUS`, confirm by hand that your mutation actually targeted the claim's
subject.

Mutation is **optional**. Some claims have no meaningful mutation, and forcing
one manufactures false findings faster than it finds real ones.

---

## What this does not check

Stated plainly, because a checker whose boundary is undocumented gets trusted
past it:

- **Whether `verify` is the semantically right command for its statement.** A
  plausible-looking command that proves the wrong thing passes everything here.
- **`evidence` artefacts** are parsed and ignored.
- **Whether the claim is worth making.** It checks the arrow, not the target.
- **Prose in your docs.** Numbers there decay; nothing compares them to live
  sources.
- **Cross-repo claims.** `verify` runs with the repo root as cwd and nothing
  else.

### Security, before you wire this into a public repo

`spine-check` executes shell commands **taken from `spine.manifest.json`**. If
anyone can open a pull request against your repository, they can therefore
execute arbitrary commands in your CI job — and `--vacuity` additionally
**writes** to the working tree.

This is the same trust model as running a fork's own test suite in CI, which is
normal. It is not *materially* worse, but it is not nothing:

- Prefer running `--claims` on trusted branches and `--adrs` everywhere.
- Do not enable `--vacuity` on untrusted pull requests.
- `mutate` is not confined to the repository root — it can write anywhere the
  runner can. That is inherent to "run this shell command", not a defect.

---

## Exit codes

| code | meaning |
|---|---|
| `0` | every enabled check passed |
| `1` | a claim failed or timed out; was skipped under `--ci`; or is `VACUOUS`/`DENIED` |
| `2` | manifest unusable, or `--adrs` found a violation |

Non-zero is red. Treat a `VACUOUS` finding as something to investigate, not
something to suppress.