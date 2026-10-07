#!/bin/sh
# Claim: the spine's own suite passes, including the tamper tests that prove
# the checker detects a broken claim.
#
# This deliberately does NOT run `spine-check` over this repo. That would be
# recursive: spine-check reads this manifest, runs this claim, which runs
# spine-check, which reads this manifest again. The first version did exactly
# that and hung. The test suite is the non-recursive equivalent evidence — it
# contains test_tamper.py, which attacks the checker directly.
set -e
exec python3 -m pytest -q
