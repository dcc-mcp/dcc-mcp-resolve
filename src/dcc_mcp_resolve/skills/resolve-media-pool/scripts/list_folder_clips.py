"""List the clips held directly in one named media pool folder."""

import sys

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_resolve.skill_support import absent_host_result, host_app, inspection_result, print_cli_result

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


def _find_folder(folder, name):
    """Depth-first lookup of a media pool folder by exact name."""
    if name is None or name == "" or folder.GetName() == name:
        return folder
    for subfolder in folder.GetSubFolderList():
        found = _find_folder(subfolder, name)
        if found is not None:
            return found
    return None


def _pool_root(app):
    project = app.GetProjectManager().GetCurrentProject()
    if project is None:
        return None
    pool = project.GetMediaPool()
    return pool.GetRootFolder() if pool else None


@skill_entry
def main(folder: str = "") -> dict:
    app, report = host_app()
    if app is None:
        return inspection_result(
            "DaVinci Resolve is not reachable", absent_host_result(report, {"folder": None, "clips": []})
        )

    root = _pool_root(app)
    if root is None:
        return inspection_result(
            "No project is open in Resolve",
            {"host_available": True, "transport": report["transport"], "folder": None, "clips": []},
        )

    target = _find_folder(root, folder)
    if target is None:
        payload = {
            "host_available": True,
            "transport": report["transport"],
            "folder": folder,
            "found": False,
            "clips": [],
        }
        return inspection_result("No media pool folder named %r" % folder, payload)

    clips = [_clip_summary(item) for item in target.GetClipList()]
    payload = {
        "host_available": True,
        "transport": report["transport"],
        "folder": target.GetName(),
        "found": True,
        "clip_count": len(clips),
        "clips": clips,
    }
    return inspection_result("Clips in media pool folder %r" % target.GetName(), payload)


def cli_main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", default="")
    args = parser.parse_args()
    return print_cli_result(main(folder=args.folder))


if __name__ == "__main__":
    sys.exit(cli_main())
