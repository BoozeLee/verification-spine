"""spine-check — prove every claim carries re-runnable evidence.

The single source of the version. pyproject.toml reads it (hatchling dynamic
version), the wheel metadata carries it, and `spine-check --version` prints
it — one number, three consumers, no second hardcoded copy to drift.
"""

__version__ = "0.1.1"
