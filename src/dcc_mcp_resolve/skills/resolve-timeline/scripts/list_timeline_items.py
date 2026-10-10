"""List the items on one track of one timeline."""

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


def _validate_track(track_type, track_index, counts):
    """Validate a one-based track index against a timeline's track counts."""
    if track_type not in TRACK_TYPES:
        return {
            "code": "invalid_track_type",
            "message": "track_type must be one of %s" % ", ".join(TRACK_TYPES),
        }
    if isinstance(track_index, bool) or not isinstance(track_index, int) or track_index < 1:
        return {"code": "invalid_track_index", "message": "track_index must be a positive integer"}
    if track_index > counts[track_type]:
        return {
            "code": "out_of_range",
            "message": "Track %s %s is out of range; the timeline has %s"
            % (track_type, track_index, counts[track_type]),
        }
    return None


def _item_summary(item):
    pool_item = item.GetMediaPoolItem()
    return {
        "name": item.GetName(),
        "duration": item.GetDuration(),
        "start": item.GetStart(),
        "end": item.GetEnd(),
        "media_pool_item": pool_item.GetName() if pool_item else None,
    }


@skill_entry
def main(
    name: Optional[str] = None,
    index: int = 0,
    track_type: str = "video",
    track_index: int = 1,
) -> dict:
    app, report = host_app()
    if app is None:
        return inspection_result(
            "DaVinci Resolve is not reachable",
            absent_host_result(report, {"timeline": None, "items": [], "item_count": 0}),
        )

    timeline, summary, error = _select(app, name, index)
    payload = {
        "host_available": True,
        "transport": report["transport"],
        "timeline": summary,
        "track_type": track_type,
        "track_index": track_index,
        "items": [],
        "item_count": 0,
    }
    if error is not None:
        payload["error_code"] = error["code"]
        return inspection_result(error["message"], payload, error=error["code"])

    track_error = _validate_track(track_type, track_index, summary["track_counts"])
    if track_error is not None:
        payload["error_code"] = track_error["code"]
        return inspection_result(track_error["message"], payload, error=track_error["code"])

    items = [_item_summary(item) for item in timeline.GetItemListInTrack(track_type, track_index)]
    payload["items"] = items
    payload["item_count"] = len(items)
    return inspection_result(
        "Items on %s track %s of timeline %r" % (track_type, track_index, summary["name"]), payload
    )


def cli_main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default=None)
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--track-type", default="video", choices=list(TRACK_TYPES))
    parser.add_argument("--track-index", type=int, default=1)
    args = parser.parse_args()
    return print_cli_result(
        main(name=args.name, index=args.index, track_type=args.track_type, track_index=args.track_index)
    )


if __name__ == "__main__":
    sys.exit(cli_main())
