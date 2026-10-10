"""Report the Resolve host version, edition, active transport, and adapter identity."""

import sys

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_resolve.runtime import environment_report, external_scripting_expected_to_work
from dcc_mcp_resolve.skill_support import inspection_result, print_cli_result


@skill_entry
def main() -> dict:
    report = environment_report()
    report["external_scripting_allowed"] = external_scripting_expected_to_work(report)
    if not report["host_available"] and not report["transport_error"]:
        report["note"] = "DaVinci Resolve is not reachable; start Resolve and retry."
    return inspection_result("Resolve session readiness", report)


def cli_main():
    return print_cli_result(main())


if __name__ == "__main__":
    sys.exit(cli_main())
