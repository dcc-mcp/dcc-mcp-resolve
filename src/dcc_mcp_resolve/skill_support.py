"""Shared structured-result and standalone CLI helpers for inspection skills.

The host is reached through :func:`host_app`, which keeps one rule for every
skill: a host that is absent is a *result* the tool reports, while a host that
cannot be reached for a configuration reason is an *error* the tool fails with.
"""

import json

from dcc_mcp_core.skill import skill_error, skill_success

from .runtime import environment_report, transport_fault_for
from .transport import TransportConfigError, resolve_app, resolve_transport


def inspection_result(message, data, error=None):
    """Build a structured skill result.

    ``error`` carries a domain error code (``not_found``, ``out_of_range``,
    ``invalid_index`` and friends). Those are genuine failures and must come
    back as failures: a caller that asked for a timeline which does not exist
    should not be told the call succeeded with an empty payload.
    """
    if data.get("transport_error"):
        return skill_error(data["transport_error"], "transport_configuration", **data)
    if error is not None:
        return skill_error(message, error, **data)
    return skill_success(message, **data)


def host_app(transport=None, environ=None):
    """Return the live Resolve application object, or ``None`` when absent.

    Raises :class:`TransportConfigError` when the transport is misconfigured or
    the host edition cannot serve it. Callers must let that propagate so the
    skill reports ``transport_configuration`` rather than pretending the host is
    merely not running.
    """
    report = environment_report(transport=transport, environ=environ)
    if report["transport_error"]:
        raise TransportConfigError(report["transport_error"])
    fault = transport_fault_for(report)
    if fault is not None:
        raise fault
    if not report["host_available"]:
        return None, report
    if report["transport_supported"] is None:
        raise TransportConfigError("Host version or edition is unknown; transport support is not established")
    return resolve_app(report["transport"], environ=environ), report


def absent_host_result(report, empty_fields):
    """Build the standard "host is not running" result payload.

    ``empty_fields`` maps result keys to the empty value a caller should see
    when there is nothing to report; using an explicit mapping keeps the shape
    stable across transports instead of letting keys disappear.
    """
    result = {"host_available": False}
    if report.get("transport_error"):
        result["transport_error"] = report["transport_error"]
    else:
        result["note"] = "DaVinci Resolve is not reachable; start Resolve and retry."
    result.update(empty_fields)
    return result


def print_cli_result(result):
    """Preserve the standalone JSON payload without printing during MCP calls."""
    print(json.dumps(result.get("context") or result, indent=2))
    return 0 if result["success"] else 1


def transport_of(report):
    """The transport a report describes, resolved once for callers."""
    return resolve_transport(report["transport"])
