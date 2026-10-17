---
name: resolve-project
description: "Inspect the current DaVinci Resolve project: name, timeline count, frame rate, resolution and settings."
license: MIT
metadata:
  dcc-mcp:
    dcc: resolve
    layer: host
    tools: tools.yaml
    version: "0.1.0"
---

# Resolve Project

Read-only inspection of the project currently open in DaVinci Resolve.

## When to use

Reach for this before mutating anything, so the tool call can name the project
it is about to touch. The frame rate and resolution reported here are the
project-level settings, which are what a deliver job will render at.

## Tools

- `project_info` — name, timeline count, frame rate, resolution, and dirty state.

## Constraints

- A real Resolve host must be running and reachable over the selected transport.
  Free releases before 21.1 have a declared `in_process` path (a Python script
  launched inside Resolve). Free 21.1+ cannot run this Python adapter.
- Project settings are returned as Resolve reports them; a setting that has
  never been changed from the project default is reported as absent rather than
  guessed at.
