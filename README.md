# dcc-mcp-resolve

DaVinci Resolve adapter for [DCC-MCP](https://github.com/dcc-mcp): project,
media pool, timeline and gallery inspection for AI agents driving Blackmagic
Design DaVinci Resolve.

Resolve is the first NLE and the first colour-grading tool in the DCC-MCP
ecosystem, filling the editing-and-finishing gap alongside `dcc-mcp-premiere`,
`dcc-mcp-kdenlive` and `dcc-mcp-capcut`.

## Status

**Alpha.** The adapter ships read-only inspection tools. Host-side behaviour is
verified on a real Resolve installation and is **not** covered by the current
host-free CI suite — see [Unverified in CI](#unverified-in-ci).

| | |
|---|---|
| Host | DaVinci Resolve 21.1 (Blackmagic Design), Windows / macOS / Linux |
| Supported lines | Resolve 18.x – 21.x |
| Python | `>=3.7` (PIP-2519 red line) |
| Core | `dcc-mcp-core>=0.20.40,<1.0.0` |

## Before you start: the Studio requirement

**External scripting is a DaVinci Resolve Studio feature from Resolve 19.1
onward.** The free edition cannot be reached by another process at all. This is
a licensing boundary in Resolve itself, not a limitation of this adapter, and it
decides which transport you can use:

| Edition | `external` | `in_process` |
|---|---|---|
| Resolve Studio 19.1+ | Yes — full coverage, the primary path | Yes |
| Free Resolve 19.1+ | **No** | Yes — the only path |
| Any Resolve ≤ 19.0 | Yes | Yes |

`dcc-mcp-resolve doctor` reports `host_edition` and
`external_scripting_allowed` so you can tell a licensing wall apart from a host
that is simply not running. On the free edition it tells you to switch to
`in_process` rather than to start Resolve again.

## Install

```bash
pip install dcc-mcp-resolve
```

See [install.md](install.md) for the host-side setup for each transport.

## Transports

Resolve is reachable two ways, and the one you pick decides what is possible.
The choice is recorded in [ADR 0001](docs/adr/0001-transport.md).

### `external` (default)

The adapter runs in its own process and connects to a running Resolve through
the external scripting API.

- Full coverage of the documented API surface; no human click needed to start.
- **Requires DaVinci Resolve Studio** from Resolve 19.1 onward.
- Requires `RESOLVE_SCRIPT_API` and `RESOLVE_SCRIPT_LIB` to point at the
  installed `Developer/Scripting` directory and the `fusionscript` library.

```bash
export RESOLVE_SCRIPT_API="/opt/resolve/Developer/Scripting"
export RESOLVE_SCRIPT_LIB="/opt/resolve/libs/Fusion/fusionscript.so"
dcc-mcp-resolve serve
```

### `in_process`

The adapter runs *inside* Resolve as a script launched from
`Workspace > Scripts`, where Resolve injects a `resolve` global.

- The **only** path on the free edition.
- Needs a human to launch the script from the menu.
- Does not cover render/deliver or the colour page the way the external API
  does.

```bash
export DCC_MCP_RESOLVE_TRANSPORT=in_process
dcc-mcp-resolve serve --pid <resolve-pid>
```

## Usage

```bash
dcc-mcp-resolve doctor          # readiness report as JSON
dcc-mcp-resolve --version
```

Agents reach the adapter through the shared gateway rather than importing the
package:

```bash
dcc-mcp-cli search --query "list resolve timelines" --dcc-type resolve
dcc-mcp-cli describe <tool-slug>
dcc-mcp-cli call <tool-slug> --json '{}'
```

## Bundled skills

Every tool is typed and validated. All of them are read-only.

| Skill | Tools |
|---|---|
| `resolve-session` | `session_info`, `list_projects` |
| `resolve-project` | `project_info` |
| `resolve-media-pool` | `list_media_pool`, `list_folder_clips` |
| `resolve-timeline` | `list_timelines`, `timeline_info`, `list_timeline_items` |
| `resolve-gallery` | `list_gallery_albums`, `list_gallery_stills` |

### Relationship to Resolve's built-in MCP server

Resolve Studio 21.1 ships its own MCP server (`ResolveMCP.exe`, about 14 tools)
whose centrepiece is a `run_script` escape hatch plus script-documentation
retrieval. This adapter deliberately does **not** clone that: it exposes typed,
parameter-validated operations instead of a generic script-execution
passthrough. A test asserts that no bundled tool is named `run_script`,
`exec_script`, `execute` or similar.

## Unverified in CI

CI runs contract checks, lint, packaging and a host-free pytest suite. It does
**not** launch DaVinci Resolve: doing so would need a Studio licence and, for
the `in_process` transport, a GUI session.

The following are therefore **not verified by CI** and rely on manual host
validation:

- Any call that reaches the Resolve scripting API.
- The Studio-only external-scripting gate against a real free-edition host.
- Scripting-directory and `fusionscript` library discovery on a real install.
- Real render, deliver and project-mutation behaviour.

When a host-side check is run manually, record it under `docs/validation/`. Do
not mark an item verified on the strength of a green CI run.

## Development

```bash
python -m pip install -e ".[test]"
python -m pytest -q
python -m ruff check src tests
python -m ruff format --check src tests
python -m build
```

## License

MIT — see [LICENSE](LICENSE).
