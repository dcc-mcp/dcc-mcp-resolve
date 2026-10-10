---
name: resolve-session
description: "Inspect the running DaVinci Resolve instance: version, edition, transport, database and project list."
license: MIT
metadata:
  dcc-mcp:
    dcc: resolve
    layer: host
    tools: tools.yaml
    version: "0.1.0"
---

# Resolve Session

Read-only inspection of the DaVinci Resolve instance the adapter is attached to.

## When to use

Use this skill first when you need to know *which* Resolve you are talking to
before doing work. The edition matters more here than in any other adapter:
from Resolve 19.1 onward **external scripting is a Studio-only feature**, so a
free-edition host cannot be reached by the `external` transport at all. This
skill reports the edition so you can tell a licensing wall apart from a host
that is simply not running.

## Tools

- `session_info` — host version, edition, transport, and adapter identity.
- `list_projects` — the projects in the current database.

## Constraints

- Every host-facing call in this skill needs a running, reachable Resolve; when
  the host is absent the tools report `host_available: false` rather than
  failing the MCP call. A *misconfigured* transport (scripting directory not
  found, or free edition on `external`) is a different thing and is reported as
  a `transport_configuration` error.
- On the `external` transport, `RESOLVE_SCRIPT_API` must point at Resolve's
  `Developer/Scripting` directory.
- Resolve 21.1 ships its own MCP server (`ResolveMCP.exe`). This adapter does
  not duplicate it: it exposes typed, validated tools instead of a generic
  script-execution escape hatch.
