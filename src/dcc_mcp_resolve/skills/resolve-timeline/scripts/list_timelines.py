"""List every timeline in the current project with its track counts."""

import sys

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_resolve.skill_support import absent_host_result, host_app, inspection_result, print_cli_result

TRACK_TYPES = ("video", "audio", "subtitle")


def _timelines_of(app):
    """Every timeline in the current project, as ``(timeline, index)`` pairs.

    Resolve's ``GetTimelineByIndex`` is one-based; the index reported outwards
    is zero-based, because that is what a caller selects by.
    """
    project = app.GetProjectManager().GetCurrentProject()
    if project is None:
        return []
    return [(project.GetTimelineByIndex(offset + 1), offset) for offset in range(project.GetTimelineCount())]


def _summary(timeline, index):
    return {
        "index": index,
        "name": timeline.GetName(),
        "duration": timeline.GetEndFrame() - timeline.GetStartFrame(),
        "start_frame": timeline.GetStartFrame(),
        "end_frame": timeline.GetEndFrame(),
        "start_timecode": timeline.GetStartTimecode(),
        "track_counts": {kind: timeline.GetTrackCount(kind) for kind in TRACK_TYPES},
    }


@skill_entry
def main() -> dict:
    app, report = host_app()
    if app is None:
        return inspection_result(
            "DaVinci Resolve is not reachable", absent_host_result(report, {"timelines": [], "timeline_count": 0})
        )

    timelines = [_summary(timeline, index) for timeline, index in _timelines_of(app)]
    return inspection_result(
        "Timelines in the current Resolve project",
        {
            "host_available": True,
            "transport": report["transport"],
            "timeline_count": len(timelines),
            "timelines": timelines,
        },
    )


def cli_main():
    return print_cli_result(main())


if __name__ == "__main__":
    sys.exit(cli_main())
