"""Report name, timeline count, frame rate and resolution of the current Resolve project."""

import sys

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_resolve.skill_support import absent_host_result, host_app, inspection_result, print_cli_result

# Project settings are read by name; a key Resolve does not report is left out
# of the result rather than filled in with an assumed default.
SETTING_KEYS = ("timelineFrameRate", "timelineResolutionWidth", "timelineResolutionHeight")


def _project_summary(project):
    settings = {}
    for key in SETTING_KEYS:
        value = project.GetSetting(key)
        if value is not None and value != "":
            settings[key] = value
    return {
        "name": project.GetName(),
        "timeline_count": project.GetTimelineCount(),
        "current_timeline": _current_timeline_name(project),
        "settings": settings,
    }


def _current_timeline_name(project):
    timeline = project.GetCurrentTimeline()
    return timeline.GetName() if timeline else None


@skill_entry
def main() -> dict:
    app, report = host_app()
    if app is None:
        return inspection_result("DaVinci Resolve is not reachable", absent_host_result(report, {"project": None}))

    project = app.GetProjectManager().GetCurrentProject()
    if project is None:
        return inspection_result(
            "No project is open in Resolve",
            {"host_available": True, "transport": report["transport"], "project": None},
        )
    return inspection_result(
        "Current Resolve project",
        {"host_available": True, "transport": report["transport"], "project": _project_summary(project)},
    )


def cli_main():
    return print_cli_result(main())


if __name__ == "__main__":
    sys.exit(cli_main())
