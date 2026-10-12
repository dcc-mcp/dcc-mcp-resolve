"""Install SOP self-check and report assembly.

The doctor is where the adapter turns what :mod:`dcc_mcp_resolve.runtime` can
see into an Install SOP report, then validates that report against the schema
Core publishes. Reading the schema revision from Core rather than re-declaring
it locally is what keeps the report from drifting when Core republishes the
artifact (contract rule A002).

The one diagnosis the doctor must get right is the edition gate: the free
edition cannot accept external scripting; free 21.1+ cannot use Python at all,
and failing that case with "start DaVinci Resolve" would send the user after a
problem that starting Resolve cannot fix.
"""

from . import __version__
from .runtime import build_report_for, transport_fault_for, transport_support_for

try:  # Core >= 0.20.40, which is this package's declared floor.
    from dcc_mcp_core import install_sop_report_schema_version, validate_install_sop_report
except ImportError:  # pragma: no cover - defensive; the floor guarantees it
    install_sop_report_schema_version = None
    validate_install_sop_report = None

DCC_TYPE = "resolve"

INSTALL_STEPS = (
    ("package", "install the dcc-mcp-resolve package"),
    ("host", "make DaVinci Resolve reachable over the selected transport"),
    ("verify", "confirm the host version and edition match the transport"),
)


def schema_version():
    """The report schema revision, read from Core when Core exposes it."""
    if install_sop_report_schema_version is not None:
        return install_sop_report_schema_version()
    return None


def core_version():
    """The installed dcc-mcp-core version, or ``None`` when unavailable."""
    try:
        import dcc_mcp_core
    except ImportError:  # pragma: no cover - defensive; the floor guarantees it
        return None
    return getattr(dcc_mcp_core, "__version__", None)


def _steps(env):
    """Map the readiness checks onto the Install SOP step list."""
    verify_ok = bool(env["host_version_supported"]) and transport_support_for(env) is True and env["python_bitness_ok"]
    return [
        {"id": "install-package", "status": "ok", "description": INSTALL_STEPS[0][1]},
        {
            "id": "connect-host",
            "status": "ok" if env["host_available"] else "planned",
            "description": INSTALL_STEPS[1][1],
        },
        {
            "id": "verify-host",
            "status": "ok" if verify_ok else "planned",
            "description": INSTALL_STEPS[2][1],
        },
    ]


def _version_diagnosis(env):
    """Whether the host version is unrecognized, unsupported, or neither.

    An unparseable version such as ``21.bad`` is *unknown*, not evidence of a
    release line outside the matrix. Only a version that parses and still falls
    outside the supported major lines is genuinely unsupported, and only that
    case should be told to upgrade.
    """
    from .compat import is_supported, major_line, parse_version_string

    raw = env.get("host_version")
    if not is_supported(raw):
        if parse_version_string(raw)[0] is None:
            return "unknown"
        if major_line(raw):
            return "unsupported"
    return None


def _verify_block(env):
    """Explain why this install is or is not directly usable.

    The edition gate is checked *before* the generic "host unreachable" branch:
    on a free-edition host over the external transport, ``host_available`` is
    false for a licensing reason, and reporting that as ``host`` would tell the
    user to start Resolve.
    """
    edition_fault = transport_fault_for(env)
    usable = bool(
        env["host_available"]
        and env["host_version_supported"]
        and env["python_bitness_ok"]
        and transport_support_for(env) is True
    )
    reason = None
    stage = None
    if env.get("transport_error"):
        stage, reason = "transport", env["transport_error"]
    elif edition_fault is not None:
        stage, reason = "transport", str(edition_fault)
    elif not env["host_available"]:
        stage, reason = "host", "DaVinci Resolve is not reachable over the selected transport"
    elif _version_diagnosis(env) == "unknown":
        stage, reason = "verify", "the host version could not be parsed; transport support is not established"
    elif not env["host_version_supported"]:
        stage, reason = "host", "the running Resolve version is on an unsupported line"
    elif transport_support_for(env) is None:
        stage, reason = "verify", "the host version or edition is unknown; transport support is not established"
    elif not env["python_bitness_ok"]:
        stage, reason = "verify", "the scripting API requires a 64-bit Python interpreter"
    return {"directly_usable": usable, "failure_stage": stage, "failure_reason": reason}


def _next_steps(env):
    """Concrete remediation steps, empty when the install is already usable."""
    edition_fault = transport_fault_for(env)
    if (
        env["host_available"]
        and env["host_version_supported"]
        and env["python_bitness_ok"]
        and transport_support_for(env) is True
    ):
        return []
    steps = []
    if env.get("transport_error"):
        steps.append(
            {
                "id": "fix-transport",
                "description": "Point the adapter at Resolve's Developer/Scripting directory",
                "why": env["transport_error"],
                "command": ["dcc-mcp-resolve", "doctor"],
            }
        )
    if edition_fault is not None:
        from .compat import python_scripting_allowed

        python_blocked = python_scripting_allowed(env["host_version"], env["host_product_name"]) is False
        steps.append(
            {
                "id": "review-python-requirement" if python_blocked else "switch-to-in-process",
                "description": (
                    "Review the Studio requirement: free Resolve 21.1+ cannot run this Python adapter"
                    if python_blocked
                    else "Launch the in_process adapter inside this pre-21.1 free Resolve from Workspace > Scripts"
                ),
                "why": str(edition_fault),
                "command": ["dcc-mcp-resolve", "doctor"],
            }
        )
    if env["host_available"] and transport_support_for(env) is None:
        steps.append(
            {
                "id": "verify-host-identity",
                "description": "Verify the host version and edition before claiming transport support",
                "why": "The adapter could not establish compatibility from the observed host identity.",
                "command": ["dcc-mcp-resolve", "doctor"],
            }
        )
    if not env["host_available"] and not env.get("transport_error") and edition_fault is None:
        steps.append(
            {
                "id": "start-resolve",
                "description": "Start DaVinci Resolve and retry",
                "why": "The host must be running and reachable over the selected transport.",
                "command": ["dcc-mcp-resolve", "doctor"],
            }
        )
    if env["host_available"] and _version_diagnosis(env) == "unsupported":
        steps.append(
            {
                "id": "upgrade-resolve",
                "description": "Move to a supported Resolve 18.x-21.x release",
                "why": "Older or newer major lines are not covered by the compatibility matrix.",
                "command": ["dcc-mcp-resolve", "doctor"],
            }
        )
    if not env["python_bitness_ok"]:
        steps.append(
            {
                "id": "use-64-bit-python",
                "description": "Install a 64-bit Python interpreter",
                "why": "The Resolve scripting API is documented for 64-bit Python only.",
                "command": ["dcc-mcp-resolve", "doctor"],
            }
        )
    return steps


def build_report(transport=None, environ=None):
    """Assemble an Install SOP report for this installation."""
    env = build_report_for(transport=transport, environ=environ)
    verify = _verify_block(env)
    report = {
        "schema_version": schema_version(),
        "status": "ok" if env["host_available"] and verify["directly_usable"] else "planned",
        "dcc_type": DCC_TYPE,
        "adapter_version": __version__,
        "core_version": core_version(),
        "steps": _steps(env),
        "next_steps": _next_steps(env),
        "receipt_path": None,
        "verify": verify,
    }
    report["notes"] = env["notes"]
    report["environment"] = env
    return report


def validate(report=None):
    """Validate a report against Core's schema.

    Returns ``(ok, errors)``. When Core does not expose the validator the check
    reports that instead of passing silently, so a missing Core feature never
    looks like a validated install.
    """
    if report is None:
        report = build_report()
    if validate_install_sop_report is None:
        return False, ["dcc-mcp-core does not expose validate_install_sop_report"]
    try:
        validate_install_sop_report(report)
    except Exception as exc:
        return False, [str(exc)]
    return True, []
