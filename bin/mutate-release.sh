#!/bin/sh
# Mutation for "release-artifact-installs-and-behaves": corrupt pyproject.toml
# so the build must fail. The spine snapshots and byte-restores the tree around
# this script, so the damage is guaranteed temporary. The appended key has an
# unterminated string, which is unparseable TOML for both hatchling and
# tomllib — uv build and python -m build must both reject it.
set -eu
printf '\n[tool.spine-mutation]\nthis-file-is-deliberately-broken = "\n' >> pyproject.toml
