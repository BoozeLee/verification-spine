"""Command-line surface. Owns argument parsing, reporting, and the exit code.

This module holds no rules of its own. It decides which checks are enabled, asks
`runner` and `adrs` what they found, and maps the answer onto a process exit code.

The exit code is the whole point: this tool exists to be wired into CI, so a
checker that exits 0 on partial information is worse than no checker.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from spine_check import __version__
from spine_check.adrs import check_adrs
from spine_check.models import ManifestError, load_manifest
from spine_check.runner import Outcome, run_verify
from spine_check.vacuity import ClaimState, check_claim_vacuity

EXIT_OK = 0
EXIT_FAILED_CLAIM = 1
EXIT_INVALID = 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="spine-check",
        description="Prove every claim in a manifest is backed by a command that runs.",
    )
    p.add_argument("repo", nargs="?", default=".", help="repository root (default: cwd)")
    p.add_argument(
        "--version", action="version", version=f"spine-check {__version__}"
    )
    p.add_argument(
        "--ci",
        action="store_true",
        help="treat a skipped claim as a failure — an empty test run is not a pass",
    )
    p.add_argument("--claims", action="store_true", help="run each claim's verify command")
    p.add_argument("--adrs", action="store_true", help="check ADRs name their enforcement")
    p.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="override every claim's timeout, in seconds",
    )
    p.add_argument(
        "--vacuity",
        action="store_true",
        help="run mutation campaigns: does verify notice when its subject is broken?",
    )
    p.add_argument("--verbose", action="store_true", help="include command output in the report")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])

    repo_root = Path(args.repo).expanduser().resolve()

    # Default to both checks; an explicit flag adds one without removing the other.
    run_claims = args.claims or not args.adrs
    run_adrs = args.adrs or not args.claims
    run_vacuity = args.vacuity

    try:
        manifest = load_manifest(repo_root)
    except ManifestError as exc:
        print(f"spine-check: {exc}", file=sys.stderr)
        return EXIT_INVALID

    print(f"{manifest.project} (spine v{manifest.spine_version}) — {repo_root}")

    exit_code = EXIT_OK

    if run_claims:
        for claim in manifest.claims:
            if args.timeout is not None:
                claim = replace(claim, timeout=args.timeout)
            result = run_verify(claim, repo_root)
            print(f"  claim {claim.id}: {result.describe()}")
            if args.verbose and (result.stdout or result.stderr):
                for stream, text in (("out", result.stdout), ("err", result.stderr)):
                    if text.strip():
                        print(f"    [{stream}] {text.strip()}")
            if result.outcome in (Outcome.FAIL, Outcome.TIMEOUT):
                exit_code = EXIT_FAILED_CLAIM
            elif result.outcome is Outcome.SKIP and args.ci:
                print("    skipped — under --ci this is a failure")
                exit_code = EXIT_FAILED_CLAIM

    if run_vacuity:
        for claim in manifest.claims:
            if args.timeout is not None:
                claim = replace(claim, timeout=args.timeout)
            v = check_claim_vacuity(claim, repo_root)
            rate = f" flip-rate {v.flip_rate}" if v.flip_rate else ""
            print(f"  vacuity {claim.id}: {v.state.value.upper()}{rate}")
            if args.verbose:
                print(f"    {v.reason}")
            if not v.restored:
                print("    WARNING: the working tree could not be restored — check git status")
                exit_code = EXIT_FAILED_CLAIM
            if v.state in (ClaimState.VACUOUS, ClaimState.DENIED):
                exit_code = EXIT_FAILED_CLAIM
            elif v.state is ClaimState.UNPROVABLE and args.ci:
                exit_code = EXIT_FAILED_CLAIM

    if run_adrs:
        violations = check_adrs(repo_root, manifest)
        for violation in violations:
            print(f"  adr {violation}")
        if violations:
            exit_code = EXIT_INVALID

    if exit_code == EXIT_OK:
        print("spine-check: OK")
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())