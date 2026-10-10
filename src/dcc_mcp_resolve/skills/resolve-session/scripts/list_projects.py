"""List the projects in the current DaVinci Resolve database."""

import sys

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_resolve.skill_support import absent_host_result, host_app, inspection_result, print_cli_result


@skill_entry
def main() -> dict:
    app, report = host_app()
    if app is None:
        return inspection_result(
            "DaVinci Resolve is not reachable", absent_host_result(report, {"project_count": 0, "projects": []})
        )

    manager = app.GetProjectManager()
    names = list(manager.GetProjectListInCurrentFolder()) if manager else []
    current = manager.GetCurrentProject() if manager else None
    current_name = current.GetName() if current else None
    projects = [{"name": name, "current": name == current_name} for name in names]
    return inspection_result(
        "Projects in the current Resolve database",
        {
            "host_available": True,
            "transport": report["transport"],
            "project_count": len(projects),
            "current_project": current_name,
            "projects": projects,
        },
    )


def cli_main():
    return print_cli_result(main())


if __name__ == "__main__":
    sys.exit(cli_main())
