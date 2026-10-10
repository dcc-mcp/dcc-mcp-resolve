---
name: resolve-timeline
description: "Inspect DaVinci Resolve timelines: track counts, duration, start timecode, and the items on a video or audio track."
license: MIT
metadata:
  dcc-mcp:
    dcc: resolve
    layer: host
    tools: tools.yaml
    version: "0.1.0"
---

# Resolve Timeline

Read-only inspection of the timelines in the current Resolve project.

## When to use

Use this to describe what is on a timeline before editing or rendering it.
`list_timelines` gives the project-level inventory; `timeline_info` and
`list_timeline_items` drill into one timeline, chosen either by name or by
index.

## Tools

- `list_timelines` — every timeline in the project with its track counts.
- `timeline_info` — duration, start timecode and track counts for one timeline.
- `list_timeline_items` — the items on one track of one timeline.

## Constraints

- A real Resolve host must be running and reachable over the selected transport.
- A timeline is selected by `name` when given, otherwise by `index` (0-based,
  defaulting to 0). A name that matches nothing is reported as not found rather
  than silently falling back to the first timeline.
- Track type is validated: only `video`, `audio` and `subtitle` are accepted,
  and an out-of-range track index is reported as such.
