---
name: resolve-gallery
description: "Inspect the DaVinci Resolve color gallery: still albums and the stills inside them."
license: MIT
metadata:
  dcc-mcp:
    dcc: resolve
    layer: host
    tools: tools.yaml
    version: "0.1.0"
---

# Resolve Gallery

Read-only inspection of the color gallery of the current Resolve project.

## When to use

Use this to discover saved stills and grades before applying one. Stills live in
albums inside the project's gallery, and a still is the usual way a saved grade
is carried between shots or projects.

## Tools

- `list_gallery_albums` — the still albums in the project gallery.
- `list_gallery_stills` — the stills in one named album.

## Constraints

- A real Resolve host must be running and reachable over the selected transport.
  Gallery access is a color-page surface, so on the free edition it is only
  reachable through the `in_process` transport.
- Album lookup is by exact name. A name that matches nothing is reported as not
  found rather than falling back to the first album.
