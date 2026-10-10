"""Walk the media pool folder tree and list the clips held directly in each folder."""

import sys
from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_resolve.skill_support import absent_host_result, host_app, inspection_result, print_cli_result

# Clip properties are read by name; a property Resolve does not report for a
# given clip is omitted rather than defaulted, so callers can tell "empty" from
# "not applicable".
CLIP_PROPERTY_KEYS = (
    "File Path",
    "Resolution",
    "Frames",
    "Frame Rate",
    "Duration",
    "Type",
    "Date Created",
)


def _clip_summary(item):
    properties = {}
    for key in CLIP_PROPERTY_KEYS:
        value = item.GetClipProperty(key)
        if value is not None and value != "":
            properties[key] = value
    return {"name": item.GetName(), "properties": properties}


def _walk_folder(folder, max_depth: Optional[int] = None, depth: int = 1):
    subfolders = folder.GetSubFolderList()
    entry = {
        "depth": depth,
        "name": folder.GetName(),
        "subfolder_count": len(subfolders),
        "clips": [_clip_summary(item) for item in folder.GetClipList()],
    }
    if max_depth is not None and depth >= max_depth:
        return [entry]
    entries = [entry]
    for subfolder in subfolders:
        entries.extend(_walk_folder(subfolder, max_depth, depth + 1))
    return entries


def _pool_root(app):
    """The current project's media pool root folder, or ``None`` if unavailable."""
    project = app.GetProjectManager().GetCurrentProject()
    if project is None:
        return None
    pool = project.GetMediaPool()
    return pool.GetRootFolder() if pool else None


@skill_entry
def main(max_depth: Optional[int] = None) -> dict:
    if max_depth is not None and (isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 1):
        raise ValueError("max_depth must be a positive integer")

    app, report = host_app()
    if app is None:
        return inspection_result(
            "DaVinci Resolve is not reachable", absent_host_result(report, {"folders": [], "folder_count": 0})
        )

    root = _pool_root(app)
    if root is None:
        return inspection_result(
            "No project is open in Resolve",
            {"host_available": True, "transport": report["transport"], "folders": [], "folder_count": 0},
        )

    folders = _walk_folder(root, max_depth)
    return inspection_result(
        "Resolve media pool tree",
        {
            "host_available": True,
            "transport": report["transport"],
            "folder_count": len(folders),
            "folders": folders,
        },
    )


def cli_main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-depth", type=int, default=None)
    args = parser.parse_args()
    return print_cli_result(main(max_depth=args.max_depth))


if __name__ == "__main__":
    sys.exit(cli_main())
