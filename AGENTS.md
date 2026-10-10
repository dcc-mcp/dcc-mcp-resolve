# AGENTS.md — dcc-mcp-resolve

> Navigation map for AI agents, not a reference manual. Detailed API lives in
> `README.md`; install and lifecycle in `install.md`; the transport decision in
> `docs/adr/0001-transport.md`. **This file is the only agent contract file at
> the repository root** — `CLAUDE.md` / `GEMINI.md` / `COPILOT.md` and friends
> are deliberately absent; agents looking for a vendor-named entry point should
> read this file.

## Build & test

```bash
python -m pip install -e ".[test]"        # editable install with the test extra
python -m pytest -q                       # host-free suite (the default local run)
python -m pytest -m resolve -q            # host lane: needs a running Resolve
python -m ruff check src tests            # lint
python -m ruff format --check src tests   # format check
python -m build                           # wheel + sdist
python -m twine check dist/*              # distribution metadata check
```

Use the `dev` extra for the lint, build and distribution gates.

- **Python:** `>=3.7`. The CI matrix covers 3.7–3.12, so keep syntax and
  dependencies importable on 3.7 unless a job explicitly excludes it.
- **Core pin:** `dcc-mcp-core>=0.20.40,<1.0.0`. Do not lower it without running
  `tests/test_doctor.py`: Core only serves `install_sop_report_schema_version()`
  and `validate_install_sop_report()` from 0.20.40 onward.

## The one thing to know before editing

**External scripting is a DaVinci Resolve Studio feature from Resolve 19.1
onward.** The free edition refuses connections from another process. That single
licensing fact is why this adapter has two transports and why `doctor` reports
the host edition. Three consequences:

1. Never report a free-edition host on the `external` transport as "Resolve is
   not reachable" — the user cannot fix that by starting Resolve. The doctor
   stages it as `transport` with a `switch-to-in-process` next step.
2. `compat.external_scripting_allowed()` returns `None` (unknown), not `False`,
   when the host version cannot be parsed. Do not flatten that into a negative.
3. Nothing may import a host module at import time. A machine without Resolve
   installed must still be able to `pip install` and run `doctor`.

CI does not launch Resolve. Tests needing a live host are marked `resolve` and
skipped by default. Do not write a test that silently passes without a host:
assert on `host_available: false` explicitly, or mark the test `resolve`.

## Repo layout

| Path | Role |
|---|---|
| `src/dcc_mcp_resolve/` | Adapter package |
| `src/dcc_mcp_resolve/transport.py` | Transport selection + scripting discovery |
| `src/dcc_mcp_resolve/runtime.py` | Host discovery and readiness reporting |
| `src/dcc_mcp_resolve/doctor.py` | Install SOP report assembly and validation |
| `src/dcc_mcp_resolve/server.py` | `DccServerBase` composition root |
| `src/dcc_mcp_resolve/cli.py` | `serve` / `doctor` entry points |
| `src/dcc_mcp_resolve/compat.py` | Supported Resolve lines and the Studio gate |
| `src/dcc_mcp_resolve/skills/` | Shipped `resolve-*` skills |
| `tests/` | pytest suite; host-free by default |
| `docs/adr/` | Architecture decision records |
| `docs/validation/` | Manual host-validation records |
| `install.md` | Host-side install for both transports |

## Transport rules

Two transports, selected by `DCC_MCP_RESOLVE_TRANSPORT`:

- `external` (default) — standalone process connecting over the external
  scripting socket. **Must not receive `--pid`.** Requires
  `RESOLVE_SCRIPT_API` / `RESOLVE_SCRIPT_LIB`, and **Studio** from 19.1.
- `in_process` — runs inside Resolve as a script from `Workspace > Scripts`.
  **Requires `--pid`.** The only path on the free edition; needs a human to
  launch it and does not cover render/deliver or the colour page fully.

The server constructor enforces the pairing, so a mismatch fails loudly rather
than half-binding the instance.

## Skill authoring

A skill is `SKILL.md` (YAML front matter with `name` and
`metadata.dcc-mcp.dcc: resolve`) plus `tools.yaml` plus `scripts/`.
`tests/test_skills.py` checks that structure statically — it never imports the
scripts, because importing them would need a live Resolve.

Keep tools typed and `read_only: true`. **Do not add a generic script-execution
escape hatch**: Resolve 21.1 already ships `ResolveMCP.exe` with a `run_script`
tool, and a test asserts no bundled tool is named `run_script`, `exec_script`,
`execute`, `run_lua` or `run_python`. Ship a validated, named operation instead.

## Release

- release-please drives versioning from Conventional Commits on `main`.
- `chore:` / `ci:` / `style:` / `refactor:` / `test:` / `build:` are hidden;
  `docs:` is a visible `Documentation` section. If every commit in a batch is
  hidden, release-please skips the batch entirely.

## Agent control path

Agents reach this adapter through the shared gateway, not by importing the
package:

```bash
dcc-mcp-cli search --query "<task>" --dcc-type resolve
dcc-mcp-cli describe <tool-slug>
dcc-mcp-cli call <tool-slug> --json '{}'
```
