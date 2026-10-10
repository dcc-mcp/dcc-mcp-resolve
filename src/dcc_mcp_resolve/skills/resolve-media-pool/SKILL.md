---
name: resolve-media-pool
description: "Inspect the DaVinci Resolve media pool: root folder tree, folder contents and clip properties."
license: MIT
metadata:
  dcc-mcp:
    dcc: resolve
    layer: host
    tools: tools.yaml
    version: "0.1.0"
---

# Resolve Media Pool

Read-only inspection of the media pool of the current Resolve project.

## When to use

Use this to find out what media is actually in the project before building a
timeline or a deliver job. `list_media_pool` walks the folder tree from the
root folder, so it also answers "what folders exist".

## Tools

- `list_media_pool` — the folder tree and, per folder, its clip list.
- `list_folder_clips` — the clips directly inside one folder, by name.

## Constraints

- A real Resolve host must be running and reachable over the selected transport.
- Folder lookup is by exact name and is not recursive: `list_folder_clips`
  reports clips held *directly* in the named folder, and an empty list means the
  folder holds no clips directly (it may still have subfolders).
- Clip properties are reported as Resolve reports them; a property Resolve does
  not expose for a given clip type is left out rather than defaulted.
