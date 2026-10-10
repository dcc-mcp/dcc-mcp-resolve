"""List the still albums in the project color gallery."""

import sys

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_resolve.skill_support import absent_host_result, host_app, inspection_result, print_cli_result


def _gallery_of(app):
    """The current project's color gallery, or ``None`` if unavailable."""
    project = app.GetProjectManager().GetCurrentProject()
    return project.GetGallery() if project else None


@skill_entry
def main() -> dict:
    app, report = host_app()
    if app is None:
        return inspection_result(
            "DaVinci Resolve is not reachable", absent_host_result(report, {"albums": [], "album_count": 0})
        )

    gallery = _gallery_of(app)
    if gallery is None:
        return inspection_result(
            "No project is open in Resolve",
            {"host_available": True, "transport": report["transport"], "albums": [], "album_count": 0},
        )

    albums = [{"name": album.GetName(), "still_count": len(album.GetStillList())} for album in gallery.GetAlbumList()]
    return inspection_result(
        "Still albums in the Resolve gallery",
        {
            "host_available": True,
            "transport": report["transport"],
            "album_count": len(albums),
            "albums": albums,
        },
    )


def cli_main():
    return print_cli_result(main())


if __name__ == "__main__":
    sys.exit(cli_main())
