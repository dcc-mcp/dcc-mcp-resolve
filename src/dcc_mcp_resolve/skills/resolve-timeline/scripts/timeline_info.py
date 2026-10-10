"""Report duration, start timecode and track counts for one timeline."""

import sys
from typing import Optional

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


def _select(app, name, index):
    """Resolve one timeline by name, else by index.

    Returns ``(timeline, summary, error)``; exactly one of ``summary`` and
    ``error`` is populated. Selection never silently falls back: an unknown name
    and an out-of-range index are both reported.
    """
    entries = _timelines_of(app)
    if not entries:
        return None, None, {"code": "no_project", "message": "No project is open in Resolve"}
    if index is not None and (isinstance(index, bool) or not isinstance(index, int) or index < 0):
        return None, None, {"code": "invalid_index", "message": "index must be a non-negative integer"}
    if name:
        for timeline, position in entries:
            if timeline.GetName() == name:
                return timeline, _summary(timeline, position), None
        return None, None, {"code": "not_found", "message": "No timeline named %r" % name}
    if index >= len(entries):
        return (
            None,
            None,
            {
                "code": "out_of_range",
                "message": "Timeline index %s is out of range; the project has %s" % (index, len(entries)),
            },
        )
    timeline, position = entries[index]
    return timeline, _summary(timeline, position), None


@skill_entry
def main(name: Optional[str] = None, index: int = 0) -> dict:
    app, report = host_app()
    if app is None:
        return inspection_result("DaVinci Resolve is not reachable", absent_host_result(report, {"timeline": None}))

    _timeline, summary, error = _select(app, name, index)
    payload = {"host_available": True, "transport": report["transport"], "timeline": summary}
    if error is not None:
        payload["error_code"] = error["code"]
        return inspection_result(error["message"], payload, error=error["code"])
    return inspection_result("Resolve timeline %r" % summary["name"], payload)


def cli_main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default=None)
    parser.add_argument("--index", type=int, default=0)
    args = parser.parse_args()
    return print_cli_result(main(name=args.name, index=args.index))


if __name__ == "__main__":
    sys.exit(cli_main())
