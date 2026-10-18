# Security policy

## Supported versions

| version | supported |
|---|---|
| 0.1.x | yes |

## Reporting a vulnerability

Use GitHub's **private vulnerability reporting** on this repository. Do not
open a public issue for anything that could be exploited.

## The honest threat model

`spine-check` runs whatever commands a `spine.manifest.json` names. That is
its job, and it is exactly as dangerous as handing a stranger a Makefile:

- `verify` and `mutate` execute as **subprocesses with the repository root as
  the working directory**. Read a foreign manifest's commands before running
  the tool against it.
- `verify` is **argv, never a shell**: shell metacharacters (`&&`, `;`, `||`,
  `$()`, backticks) are rejected outright, so shell composition cannot smuggle
  a second command past a reader.
- Output capture is capped at **4,000 characters per stream**, and every claim
  has a **timeout** (default 300 s, overridable in the manifest), so a runaway
  command can neither exhaust memory nor hang the gate.
- The package has **no runtime dependencies** (stdlib only) and makes **no
  network connections**. The supply chain is CPython plus this source tree.

## Scope

Out of scope: anything a manifest could do that a shell script could also do —
by design, running the tool IS running its commands. In scope: anything that
lets a command escape its argv classification, bypass the timeout, exceed the
capture cap, or make the checker exit 0 on partial information.
