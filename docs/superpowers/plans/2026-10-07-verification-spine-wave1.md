# Verification Spine — Wave 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `spine-check` — a stdlib-only CLI that proves every claim in a repository's manifest is backed by a command that actually runs, and an ADR check that rejects decisions without enforcement — then prove it by adopting the spine on `elohim`.

**Architecture:** A small Python package. `manifest.py` parses and validates `spine.manifest.json`; `runner.py` executes each claim's `verify` command in a subprocess against the repo root and classifies the outcome as pass / fail / skip / timeout; `adrs.py` enforces the `## Verification` rule; `cli.py` composes them and owns the exit code. Adoption is data, not code: a manifest plus ADRs in the target repo, with the checker run from CI.

**Tech Stack:** Python ≥ 3.10, standard library only (`json`, `subprocess`, `shlex`, `pathlib`, `re`, `argparse`). No PyYAML, no pytest, no third-party runtime dependency. Tests run under `pytest` as a dev dependency only.

**Spec:** `docs/superpowers/specs/2026-10-07-verification-spine-design.md` — the plan argues from the spec, so the spec travels with it; executors read both.

## Global Constraints

- Manifest format is **`spine.manifest.json`, not `.yaml`.** This deviates from spec §3. Rationale: YAML requires PyYAML, which breaks the spec §5 "stdlib only" constraint; `json` is in the stdlib and every adopter already has it. Record this deviation in `docs/adr/0001-*.md`.
- Exit code **5 means "skipped"** for any `verify` command. This is the pytest / `no tests collected` convention. It is the only reserved exit code.
- Default `verify` timeout is **300 seconds**, overridable per claim via `"timeout": <int>`.
- `spine-check` exits **0** only when every enabled check passes and no claim was skipped under `--ci`. It must never exit 0 on partial information.
- An ADR with status `superseded` is exempt from the `## Verification` requirement.
- Every task ends in a `git commit`. Do not push unless the user says so.
- Nothing in this plan runs before **2026-10-13**. See spec §6.

## Review Focus

Five input classes the spec implies but no task's happy-path test exercises. Each is pinned to its owning task.

1. **A `verify` command that hangs forever.** A reasonable person expects a hang to be a *failure*, never a pass — otherwise a broken gate silently satisfies itself. → Task 2
2. **A duplicated `claim.id` within one manifest** (JSON copy-paste). Expected: hard error naming the duplicate, not a silent last-one-wins. → Task 1
3. **An ADR marked `superseded by ADR-0031`.** Expected: exempt from `## Verification`; requiring it would make adopting the spine painful and would be wrong. → Task 3
4. **A manifest citing an ADR id that does not exist on disk.** Expected: hard error — a claim bound to a nonexistent decision is untraceable. → Task 3
5. **A `verify` command that exits 5 — "no tests collected".** Expected: reported as *skipped*, and under `--ci` treated as a failure. An empty test run must never read as a pass. → Task 2

---

## File Structure

```
verification-spine/
├── pyproject.toml                  # package "spine-check", hatchling, console script
├── bin/
│   └── spine-check                  # thin shim → spine_check.cli:main
├── src/spine_check/
│   ├── __init__.py                  # empty
│   ├── __main__.py                  # enables `python -m spine_check`
│   ├── models.py                    # Claim + Manifest dataclasses; parse/validate
│   ├── runner.py                    # run_verify(); ClaimOutcome
│   ├── adrs.py                      # check_adrs()
│   └── cli.py                       # main(); argument parsing; exit code
├── tests/
│   ├── fixtures/
│   │   └── repo_ok/                 # minimal conformant repo
│   │       ├── spine.manifest.json
│   │       ├── docs/adr/0001-x.md
│   │       └── verify.sh            # exits 0
│   ├── repo_bad_adrs/               # ADR missing ## Verification
│   ├── repo_dup_id/                 # manifest with a repeated claim id
│   ├── repo_dangling_adr/           # manifest citing a nonexistent ADR
│   ├── repo_timeout/                # verify.sh sleeps forever
│   └── repo_skip/                   # verify.sh exits 5
└── docs/adr/0001-manifest-is-json.md
```

Responsibility per file: `models.py` owns parsing and static validation and knows nothing about running anything. `runner.py` owns subprocess execution and owns nothing about policy. `adrs.py` owns ADR files. `cli.py` owns flags and the exit code and calls the other three.

---

### Task 1: Manifest parsing and static validation

Implements rule **R1** — every claim names a `verify` command a third party can run.

**Files:**
- Create: `pyproject.toml`
- Create: `src/spine_check/__init__.py`
- Create: `src/spine_check/__main__.py`
- Create: `src/spine_check/models.py`
- Create: `tests/fixtures/repo_ok/spine.manifest.json`, `verify.sh`, `docs/adr/0001-x.md`
- Create: `tests/fixtures/repo_dup_id/spine.manifest.json`, `verify.sh`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `class ManifestError(Exception)` — carries `.path` (str) and `.line` (int | None).
  - `class Claim` — fields `id: str`, `statement: str`, `verify: str`, `expect: str`, `timeout: int`, `evidence: str | None`, `adrs: list[str]`.
  - `class Manifest` — fields `project: str`, `spine_version: int`, `claims: list[Claim]`.
  - `load_manifest(repo_root: Path) -> Manifest` — reads `repo_root/spine.manifest.json`; raises `ManifestError`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_models.py
import json
import pytest
from spine_check.models import ManifestError, load_manifest

FIX = Path(__file__).parent / "fixtures"

def test_loads_conformant_manifest():
    m = load_manifest(FIX / "repo_ok")
    assert m.project == "fixture-repo"
    assert m.spine_version == 1
    assert [c.id for c in m.claims] == ["dummy-claim"]

def test_duplicate_claim_id_is_hard_error():
    with pytest.raises(ManifestError) as e:
        load_manifest(FIX / "repo_dup_id")
    assert "duplicate" in str(e.value).lower()
    assert "dummy-claim" in str(e.value)
```

```json
// tests/fixtures/repo_dup_id/spine.manifest.json
{
  "project": "fixture-repo",
  "spine_version": 1,
  "claims": [
    { "id": "dummy-claim", "statement": "s", "verify": "./verify.sh", "expect": "exit 0" },
    { "id": "dummy-claim", "statement": "t", "verify": "./verify.sh", "expect": "exit 0" }
  ]
}
```

`verify.sh` in both fixtures: `#!/bin/sh\nexit 0`, mode `0755`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'spine_check'`

- [ ] **Step 3: Implement `load_manifest` in `src/spine_check/models.py`**

`Claim.timeout` defaults to `300`; `evidence` and `adrs` default to `None` and `[]`. Validate in this order and raise `ManifestError` naming the offending claim: unknown top-level key; `spine_version != 1`; missing `project`; `claims` not a list; a claim missing `id`/`statement`/`verify`/`expect`; `expect` not `"exit 0"`; duplicate `id`; empty `verify`. Report the key path (`claims[2].verify`) and the JSON line number where available.

- [ ] **Step 4: Add `pyproject.toml`, `__init__.py`, `__main__.py`**

hatchling build backend, `name = "spine-check"`, `requires-python = ">=3.10"`, `[project.scripts] spine-check = "spine_check.cli:main"`. `__main__.py` calls `cli.main()`. `cli.py` may be a stub `def main() -> int: return 0` until Task 4.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_models.py -v`
Expected: PASS, 2 passed

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/spine_check/ tests/
git commit -m "feat: parse and statically validate spine manifests"
```

---

### Task 2: Verify runner

Implements rule **R2** — every `verify` executes, and skipping is visible.

**Files:**
- Create: `src/spine_check/runner.py`
- Create: `tests/fixtures/repo_timeout/verify.sh`, `tests/fixtures/repo_skip/verify.sh`
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `Claim` from Task 1.
- Produces:
  - `class Outcome(str, Enum)` — members `PASS`, `FAIL`, `SKIP`, `TIMEOUT`.
  - `class ClaimOutcome` — fields `claim_id: str`, `outcome: Outcome`, `exit_code: int | None`, `stdout: str`, `stderr: str`.
  - `SKIP_EXIT_CODES: frozenset[int]` — `{5}`.
  - `run_verify(claim: Claim, repo_root: Path) -> ClaimOutcome` — runs `shlex.split(claim.verify)` with `cwd=repo_root`, `capture_output=True`, `timeout=claim.timeout`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_runner.py
from spine_check.models import Claim
from spine_check.runner import Outcome, run_verify

FIX = Path(__file__).parent / "fixtures"

def _claim(timeout=300):
    return Claim(id="c", statement="s", verify="./verify.sh", expect="exit 0", timeout=timeout)

def test_passing_command_is_pass():
    assert run_verify(_claim(), FIX / "repo_ok").outcome is Outcome.PASS

def test_exit_5_is_skip_not_pass():
    assert run_verify(_claim(), FIX / "repo_skip").outcome is Outcome.SKIP

def test_hanging_command_is_timeout_not_pass():
    r = run_verify(_claim(timeout=2), FIX / "repo_timeout")
    assert r.outcome is Outcome.TIMEOUT

def test_failing_command_is_fail():
    r = run_verify(Claim(id="c", statement="s", verify="false", expect="exit 0", timeout=30), FIX / "repo_ok")
    assert r.outcome is Outcome.FAIL
    assert r.exit_code == 1
```

`repo_timeout/verify.sh`: `#!/bin/sh\nsleep 60`. `repo_skip/verify.sh`: `#!/bin/sh\nexit 5`. All fixture scripts mode `0755`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_runner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'spine_check.runner'`

- [ ] **Step 3: Implement `run_verify`**

`subprocess.run(shlex.split(claim.verify), cwd=repo_root, capture_output=True, text=True, timeout=claim.timeout)`. Map: `TimeoutExpired` → `Outcome.TIMEOUT` with `exit_code=None`; returncode in `SKIP_EXIT_CODES` → `SKIP`; `0` → `PASS`; anything else → `FAIL`. Truncate `stdout`/`stderr` to 4000 characters each. `FileNotFoundError` from `subprocess` → `FAIL`, not an exception escaping.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_runner.py -v`
Expected: PASS, 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/spine_check/runner.py tests/
git commit -m "feat: run claim verify commands with pass/fail/skip/timeout outcomes"
```

---

### Task 3: ADR enforcement

Implements rule **R3** — every binding decision names its enforcement.

**Files:**
- Create: `src/spine_check/adrs.py`
- Create: `tests/fixtures/repo_bad_adrs/docs/adr/0001-missing-verification.md`
- Create: `tests/fixtures/repo_dangling_adr/spine.manifest.json`, `verify.sh`
- Test: `tests/test_adrs.py`

**Interfaces:**
- Consumes: `Manifest` from Task 1 (for `claim.adrs` cross-checking).
- Produces:
  - `class AdrViolation` — fields `path: str`, `reason: str`.
  - `check_adrs(repo_root: Path, manifest: Manifest) -> list[AdrViolation]` — returns every violation found; an empty list means compliant.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_adrs.py
from spine_check.adrs import check_adrs
from spine_check.models import load_manifest

FIX = Path(__file__).parent / "fixtures"

def test_conformant_repo_has_no_violations():
    assert check_adrs(FIX / "repo_ok", load_manifest(FIX / "repo_ok")) == []

def test_adr_without_verification_section_is_a_violation():
    v = check_adrs(FIX / "repo_bad_adrs", load_manifest(FIX / "repo_ok"))
    assert any("Verification" in x.reason for x in v)

def test_superseded_adr_is_exempt():
    repo = FIX / "repo_superseded"
    assert check_adrs(repo, load_manifest(FIX / "repo_ok")) == []

def test_dangling_adr_reference_is_a_violation():
    v = check_adrs(FIX / "repo_dangling_adr", load_manifest(FIX / "repo_dangling_adr"))
    assert any("9999" in x.path or "9999" in x.reason for x in v)
```

Fixtures: `repo_bad_adrs/docs/adr/0001-missing-verification.md` has `## Context` / `## Decision` but no `## Verification`. `repo_superseded/docs/adr/0001-old.md` sets `- **Status:** superseded by ADR-0031` and omits `## Verification`. `repo_dangling_adr/spine.manifest.json` declares one claim with `"adrs": ["9999"]` and that ADR file does not exist.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_adrs.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'spine_check.adrs'`

- [ ] **Step 3: Implement `check_adrs`**

For each `*.md` under `repo_root/docs/adr/`: read it; if a line matches `^\s*-\s*\*\*Status:\*\*\s*superseded`, skip it. Otherwise require a heading matching `^##\s+Verification\b` (case-insensitive) and, beneath it before the next `##`, at least one non-empty line that is not a `<placeholder>`. Collect violations as `AdrViolation(path=str(rel_path), reason=...)`. Then, for every `claim.adrs` entry, assert a file exists whose numeric prefix matches; report `reason` naming the missing id.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_adrs.py -v`
Expected: PASS, 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/spine_check/adrs.py tests/
git commit -m "feat: enforce that every ADR names its enforcement"
```

---

### Task 4: CLI and exit codes

**Files:**
- Create: `src/spine_check/cli.py`
- Create: `bin/spine-check`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `load_manifest`, `run_verify`, `check_adrs`, `Outcome` from Tasks 1–3.
- Produces: `spine-check <repo> [--ci] [--adrs] [--claims] [--timeout N]`, exit `0` all-pass, `1` any failure/timeout, `2` manifest or ADR violation.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cli.py
from spine_check.cli import main

FIX = Path(__file__).parent / "fixtures"

def test_conformant_repo_exits_zero(capsys):
    assert main([str(FIX / "repo_ok"), "--adrs", "--claims"]) == 0

def test_failing_claim_exits_nonzero():
    assert main([str(FIX / "repo_fail")]) != 0

def test_skip_exits_zero_without_ci_flag():
    assert main([str(FIX / "repo_skip")]) == 0

def test_skip_is_failure_under_ci_flag():
    assert main([str(FIX / "repo_skip"), "--ci"]) == 1

def test_adr_violation_exits_two_under_adrs_flag():
    assert main([str(FIX / "repo_bad_adrs"), "--adrs"]) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL — `main` returns `None`, so `== 0` is False

- [ ] **Step 3: Implement `main`**

Default checks: `--claims` (run every claim) and `--adrs`. Print one line per claim as `<id>: <OUTCOME>` and one per violation. Exit `2` on `ManifestError` or when `--adrs` yields violations; `1` if any outcome is `FAIL` or `TIMEOUT`, or any `SKIP` while `--ci`; else `0`. `--timeout N` overrides every claim's timeout. A missing manifest is a `ManifestError`, not a traceback.

`bin/spine-check`: `#!/bin/sh\nexec python3 -m spine_check "$@"` — and note in the README that the installed console script is the supported path.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -v`
Expected: PASS, 5 passed

- [ ] **Step 5: Run the whole suite**

Run: `pytest -v`
Expected: PASS, 15 passed (2 + 4 + 4 + 5)

- [ ] **Step 6: Commit**

```bash
git add src/spine_check/cli.py bin/ tests/
git commit -m "feat: spine-check CLI with ci, adrs and claims flags"
```

---

### Task 5: The anti-decorative test

The test that decides whether the spine is real. If breaking a claim's evidence changes nothing, everything above was decoration.

**Files:**
- Create: `tests/test_tamper.py`
- Create: `tests/fixtures/repo_tamper/spine.manifest.json`, `verify.sh`, `docs/adr/0001-x.md`

**Interfaces:**
- Consumes: `main` from Task 4.
- Produces: no new public API. This task exists to fail loudly if the design is wrong.

- [ ] **Step 1: Write the test**

```python
# tests/test_tamper.py
import os, stat
from spine_check.cli import main

FIX = Path(__file__).parent / "fixtures"
REPO = FIX / "repo_tamper"

def test_tampering_with_a_claim_is_detected(tmp_path):
    assert main([str(REPO), "--claims", "--adrs"]) == 0, "baseline must pass first"

    v = REPO / "verify.sh"
    original = v.read_text()
    try:
        v.write_text("#!/bin/sh\nexit 1\n")
        v.chmod(v.stat().st_mode | stat.S_IEXEC)
        assert main([str(REPO), "--claims", "--adrs"]) == 1, \
            "a broken claim must fail the checker"
    finally:
        v.write_text(original)
        v.chmod(v.stat().st_mode | stat.S_IEXEC)

def test_spine_recovers_after_tamper_is_reverted():
    assert main([str(REPO), "--claims", "--adrs"]) == 0
```

`repo_tamper/verify.sh`: `#!/bin/sh\nexit 0`, mode `0755`. Its manifest declares one claim pointing at `./verify.sh` with `"adrs": ["0001"]`, and `docs/adr/0001-x.md` contains a real `## Verification` section.

- [ ] **Step 2: Run it to verify it fails for the right reason**

Run: `pytest tests/test_tamper.py -v`
Expected: FAIL, and the assertion message must be the *tamper detection* one — if it fails on the baseline `== 0` instead, the fixture is wrong, not the design. Fix the fixture before continuing.

- [ ] **Step 3: No implementation change**

This test must already pass against the Task 4 code. If it does not, the bug belongs to whichever of Tasks 1–4 let a failing claim through — fix it there, not here.

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_tamper.py -v`
Expected: PASS, 2 passed

- [ ] **Step 5: Commit**

```bash
git add tests/test_tamper.py tests/fixtures/repo_tamper/
git commit -m "test: prove the spine detects a tampered claim"
```

---

### Task 6: Adopt the spine on `elohim`

Data, not code. This is the Wave 1 pilot that tests the thesis (spec §1 — provisional at jev 0.71).

**Files:**
- Create in `~/Bakery-street-project/elohim/`: `spine.manifest.json`
- Create in `~/Bakery-street-project/elohim/`: `docs/adr/0001-residual-gate-is-the-entry-point.md`, `docs/adr/0002-manifest-is-json.md`
- Modify in `~/Bakery-street-project/elohim/`: `agentic-setup/templates/ADR-template.md` (add `## Verification`)
- Modify in `~/Bakery-street-project/elohim/`: `.github/workflows/ci.yml` (add a spine-check job)

**Interfaces:**
- Consumes: `spine-check` from Task 4.
- Produces: the evidence that the thesis holds or does not.

- [ ] **Step 1: Confirm the baseline is green before adopting**

Run: `cd ~/Bakery-street-project/elohim && python3 tests/test_all.py`
Expected: exit 0. Measured 2026-10-07 as 319 passed / 1 skipped. **If this is red, stop** — the spec's gate rule forbids adopting on a red suite, and that is the rule the spine exists to enforce.

- [ ] **Step 2: Write the manifest with two real claims**

One claim per ADR. `residual-gate-is-binding` verifies via `python3 tests/test_all.py`; `manifest-is-json` verifies via `spine-check` on the spine repo itself. Both `"expect": "exit 0"`, each naming its ADR via `"adrs"`.

- [ ] **Step 3: Write the two ADRs**

`0001` records that the residual gate is the entry point for any numerical claim — the decision `elohim` already enforces in code. `0002` records the JSON-not-YAML manifest deviation and its stdlib rationale. **Both must contain a real `## Verification` section naming the command that enforces them.** Copy the shape from `tests/fixtures/repo_ok/docs/adr/0001-x.md`.

- [ ] **Step 4: Fix the ADR template — do this before claiming adoption**

`agentic-setup/templates/ADR-template.md` has headings Context / Decision / Consequences / Rejected alternatives / Revisit when and **no `## Verification` section at all**. As written, an ADR produced from that template fails R3. Add a `## Verification` section between `## Decision` and `## Consequences` requiring the enforcing command. This was found on 2026-10-07 and is the spine's first real catch.

- [ ] **Step 5: Run the checker against `elohim`**

Run: `spine-check ~/Bakery-street-project/elohim --claims --adrs --ci`
Expected: exit 0, every claim `PASS`, no ADR violations.

- [ ] **Step 6: Prove the tamper test on the real repo**

Temporarily point one claim's `verify` at `false`, re-run Step 5, confirm exit 1, then revert and re-confirm exit 0. Do not commit the broken state.

- [ ] **Step 7: Wire it into `elohim` CI**

Add one job to `.github/workflows/ci.yml` running `spine-check . --claims --adrs --ci`. Note that CI invokes `python3 tests/test_all.py` (line 53), so the manifest's `verify` must use that same entry point, not bare `pytest`, or the spine would check a different thing than CI runs.

- [ ] **Step 8: Record what was learned**

Append to `~/verification-spine/ROADMAP.md`: whether one repo was enough to validate the thesis, and whether the `verify` command had to differ from CI's actual command. Both are evidence for or against proceeding to Wave 2 — and per spec §6, Wave 2 is conditional on this, not scheduled.

- [ ] **Step 9: Commit in both repos separately**

```bash
cd ~/Bakery-street-project/elohim && git add spine.manifest.json docs/adr/ .github/workflows/ci.yml
git commit -m "feat: adopt the verification spine — 2 claims, 2 ADRs, spine-check in CI"
cd ~/agentic-setup && git add templates/ADR-template.md
git commit -m "fix: ADR template now requires a Verification section"
```

Do not push either without the user's word.

---

## Self-Review

**1. Spec coverage.** R1 → Task 1. R2 → Task 2. R3 → Task 3. §5 enforcement + exit codes → Task 4. §9 testing incl. anti-decorative → Task 5. §6 Wave 1 pilot → Task 6. §7 non-goals (no shared library, no monorepo, opt-in) respected: nothing here imports from another project. §8 R-6 `foundation-ai-engine` fate — **not covered by a task.** Deliberately: it is a deletion decision belonging to the user, not an implementation step. Flagged in the handoff rather than silently dropped.

**2. Step scan.** Every code step names a signature and a file; test steps give test names and assertions; verification steps give command and expected output. No `TBD`, no "handle edge cases".

**3. Type consistency.** `Claim`/`Manifest`/`ManifestError` (Task 1) are consumed unchanged by `run_verify` (Task 2), `check_adrs` (Task 3), `main` (Task 4). `check_adrs` takes `(repo_root, manifest)` — Task 3's tests pass the *fixture's* manifest alongside a *different* repo path where the mismatch is irrelevant, except in `test_dangling_adr` where both are the same repo; that is deliberate and documented in the test.

**4. Review Focus.** All five classes are pinned: hang → Task 2 `test_hanging_command_is_timeout_not_pass`; duplicate id → Task 1; superseded ADR → Task 3; dangling ADR → Task 3; exit-5 skip → Task 2 and Task 4 `test_skip_is_failure_under_ci_flag`.

**5. Proportion.** Plan ≈ spec in length. Code blocks are signatures, test names and assertions — no function bodies except fixture scripts and one JSON file.