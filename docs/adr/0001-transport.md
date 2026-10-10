# ADR 0001: Resolve transport — external scripting default, in-app script fallback

- **Status:** Accepted
- **Date:** 2026-10-11
- **Host:** DaVinci Resolve 21.1 (Blackmagic Design), Windows / macOS / Linux

## Context

The adapter needs one channel over which to drive Resolve. The decision is not
a free choice, because Resolve's own licensing constrains it.

### Constraint: external scripting is Studio-only

Blackmagic's scripting API is documented in the *DaVinci Resolve Scripting
README* shipped with the application. It documents the module layout
(`$RESOLVE_SCRIPT_API/Modules/DaVinciResolveScript.py`, entry point
`scriptapp("Resolve")`), the environment variables `RESOLVE_SCRIPT_API` and
`RESOLVE_SCRIPT_LIB`, a Python >= 3.6 64-bit requirement, and support for
`-nogui` headless operation with the API still available.

From roughly Resolve 19.1, Blackmagic restricts external scripting to the paid
Studio edition ($295). The free edition cannot be reached from another process
at all; its only automation path is a Lua or Python script run manually from the
in-application `Workspace > Scripts` menu, and that path does not reach
render/deliver or the colour page in the same way.

So the two candidates are not two flavours of the same thing. One is available
only to paying users, and the other is the only option for everyone else.

### Candidate A — External scripting (`external`)

- Full documented API surface: `Resolve`, `ProjectManager`, `Project`,
  `MediaStorage`, `MediaPool`, `Folder`, `MediaPoolItem`, `Timeline`,
  `TimelineItem`, `Gallery`, `GalleryStillAlbum`, `GalleryStill`, `Graph`,
  `ColorGroup`, plus `Resolve.Fusion()` for Fusion scripting.
- Runs out of process, so it needs no human click to start and works with
  `-nogui`.
- Requires Studio from 19.1 onward.
- Requires the scripting directory and `fusionscript` library to be discoverable.

### Candidate B — In-application script (`in_process`)

- The only path on the free edition.
- Resolve injects a `resolve` global, so no connection setup is needed.
- Requires a human to launch the script from `Workspace > Scripts`.
- Does not cover render/deliver or the colour page as fully as the external API.

### Candidate C — A generic `run_script` escape hatch

Rejected. Resolve Studio 21.1 ships its own MCP server (`ResolveMCP.exe` /
`DaVinciResolve.mcpb`, roughly 14 tools) whose centrepiece is exactly this: a
`run_script` passthrough, plus script-documentation retrieval and LUT/DCTL
helpers. Cloning it would add nothing the host does not already provide, and
would undercut this adapter's actual value — typed, parameter-validated
operations. A test asserts no bundled tool is named `run_script`, `exec_script`,
`execute`, `run_lua` or `run_python`.

### Python coupling

The scripting README asks for Python >= 3.6 64-bit. Resolve also ships its own
interpreter (ResolvePython 3.14 in 21.1), and community practice clusters on
3.9–3.11. The organisation's floor is 3.7. This is handled by keeping
`requires-python = ">=3.7"` and importing every host bridge lazily inside
functions, so an unmatching interpreter yields a `doctor` finding instead of an
import-time crash.

## Decision

**Default to the external scripting transport (`external`), and keep the
in-application script transport (`in_process`) selectable through
`DCC_MCP_RESOLVE_TRANSPORT`.**

Reasons, in order of weight:

1. **Coverage.** The external transport is the only one that reaches the full
   documented surface this adapter's typed tools are built on. Choosing the
   narrower path as the default would cap the skill set before it is written.
2. **No human in the loop.** The external transport starts as an ordinary
   service. The in-process transport needs someone to click a menu item every
   time, which is fatal for unattended automation.
3. **The fallback exists and is honest.** `in_process` is a real, working path
   for the free edition, not a stub. The adapter detects the edition and says so
   rather than letting the user discover it as a mysterious connection failure.
4. **CI cannot cover either.** Both transports need a real host — the external
   one needs a Studio licence, the in-process one a GUI session. That reality is
   recorded in `docs/validation/` rather than disguised as a green CI run.

## Consequences

- `DccServerOptions.from_env("resolve", ...)` is constructed with
  `instance_type="standalone"` and no bound PID on the external transport, and
  `instance_type="gui"` with a bound `dcc_pid` on the in-process one. The two
  shapes have different liveness semantics and are validated separately.
- The doctor must classify the free-edition-on-external case as a
  **transport** failure, not a host failure. Reporting it as "Resolve is not
  reachable" would tell the user to start Resolve, which cannot fix a licensing
  gate. `runtime.transport_fault_for()` centralises that judgement.
- `compat.external_scripting_allowed()` returns `None` when the host version
  cannot be parsed, because "unknown" must not collapse into "blocked".
- No host module is imported at module scope. `DaVinciResolveScript` is imported
  inside `transport.resolve_script_module()`, so installing and running
  `doctor` on a machine without Resolve works.
- Current CI does not launch Resolve. Anything touching the scripting API needs
  host validation recorded under `docs/validation/`; a passing host-free suite
  is not evidence that either transport works against Resolve.
