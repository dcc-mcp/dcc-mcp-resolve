"""List the stills in one named gallery album."""

import sys

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_resolve.skill_support import absent_host_result, host_app, inspection_result, print_cli_result


def _gallery_of(app):
    project = app.GetProjectManager().GetCurrentProject()
    return project.GetGallery() if project else None


def _find_album(gallery, name):
    """Look up a still album by exact name.

    With no name the first album is returned, which is the natural default for a
    project holding only one. Returns ``None`` when the gallery is empty or no
    album matches.
    """
    albums = gallery.GetAlbumList()
    if not albums:
        return None
    if not name:
        return albums[0]
    for album in albums:
        if album.GetName() == name:
            return album
    return None


@skill_entry
def main(album: str = "") -> dict:
    app, report = host_app()
    if app is None:
        return inspection_result(
            "DaVinci Resolve is not reachable",
            absent_host_result(report, {"album": None, "stills": [], "still_count": 0}),
        )

    gallery = _gallery_of(app)
    if gallery is None:
        return inspection_result(
            "No project is open in Resolve",
            {
                "host_available": True,
                "transport": report["transport"],
                "album": None,
                "stills": [],
                "still_count": 0,
            },
        )

    target = _find_album(gallery, album)
    if target is None:
        payload = {
            "host_available": True,
            "transport": report["transport"],
            "album": album,
            "found": False,
            "stills": [],
            "still_count": 0,
        }
        message = "No gallery album named %r" % album if album else "The Resolve gallery holds no still albums"
        return inspection_result(message, payload)

    stills = [{"label": still.GetLabel(), "file_path": still.GetFilePath()} for still in target.GetStillList()]
    payload = {
        "host_available": True,
        "transport": report["transport"],
        "album": target.GetName(),
        "found": True,
        "still_count": len(stills),
        "stills": stills,
    }
    return inspection_result("Stills in gallery album %r" % target.GetName(), payload)


def cli_main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--album", default="")
    args = parser.parse_args()
    return print_cli_result(main(album=args.album))


if __name__ == "__main__":
    sys.exit(cli_main())
