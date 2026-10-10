"""Host discovery and readiness reporting.

Every function here is transport-aware and side-effect free with respect to the
host: they report what the adapter can see, never mutate the Resolve project.
When no running Resolve is reachable, readiness reports ``host_available:
False``.

Two distinctions matter and are kept separate throughout:

- **Host absent** (Resolve is not running) is an ordinary state reported as
  ``host_available: false`` with no error.
- **Host unusable by configuration** (scripting API not installed, or the free
  edition asked for external scripting) is a fault reported as
  ``transport_error``, because no amount of starting Resolve will fix it.
"""

import os
import platform
import sys

from .compat import (
    TARGET_VERSION,
    is_supported,
    parse_edition,
)
from .transport import (
    ENV_VAR,
    IN_PROCESS,
    SCRIPT_API_ENV,
    SCRIPT_LIB_ENV,
    EditionNotSupportedError,
    TransportConfigError,
    TransportError,
    external_resolve,
    in_process_resolve,
    resolve_transport,
    script_api_paths,
    script_lib_paths,
)


def _read_in_process():
    """Read version and product name through Resolve's injected global."""
    app = in_process_resolve()
    return {
        "version": app.GetVersionString(),
        "product": app.GetProductName(),
    }


def _read_external(environ=None):
    """Read version and product name over the external scripting socket."""
    app = external_resolve(environ=environ)
    if app is None:
        return None
    return {
        "version": app.GetVersionString(),
        "product": app.GetProductName(),
    }


def detect_host(transport=None, environ=None):
    """Return a dict describing the running Resolve, or ``None`` if absent.

    A :class:`TransportConfigError` propagates: it means the selected transport
    is misconfigured, which is not the same thing as Resolve being unreachable.

    A plain :class:`TransportError` covers the ordinary "host not there" case on
    the in-process transport -- Resolve simply never injected its ``resolve``
    global because this process is not running inside it -- and resolves to
    ``None``, exactly like an external host that declines to answer.
    """
    chosen = resolve_transport(transport, environ=environ)
    try:
        if chosen == IN_PROCESS:
            return _read_in_process()
        return _read_external(environ=environ)
    except TransportConfigError:
        raise
    except TransportError:
        return None


def detect_host_version(transport=None, environ=None):
    """Return the running Resolve version string, or ``None`` when unreachable."""
    host = detect_host(transport=transport, environ=environ)
    return None if host is None else host["version"]


def _scripting_dirs_present(environ=None):
    """Which candidate scripting directories exist on this machine."""
    import os

    return [path for path in script_api_paths(environ=environ) if os.path.isdir(path)]


def _library_present(environ=None):
    """Whether any candidate fusionscript library exists."""
    import os

    return any(os.path.isfile(path) for path in script_lib_paths(environ=environ))


def environment_report(transport=None, environ=None):
    """A JSON-serialisable readiness report for ``doctor`` and the CLI.

    A transport that cannot be honoured is reported as ``transport_error``
    rather than raised: the doctor's job is to explain a broken install, so it
    must stay runnable on one. An unreachable host is not an error, so it keeps
    the ordinary ``host_available: false`` path. ``headless_host`` is reported
    for the external transport, where the adapter genuinely connects out of
    process and cannot know whether a GUI is attached; on the in-process
    transport the host is by definition running with its UI.
    """
    env = environ if environ is not None else os.environ
    chosen = resolve_transport(transport, environ=env)
    try:
        host = detect_host(chosen, environ=env)
        transport_error = None
    except TransportConfigError as exc:
        host = None
        transport_error = str(exc)

    version = None if host is None else host["version"]
    product = None if host is None else host["product"]
    edition = parse_edition(product) if product else None
    script_dirs = _scripting_dirs_present(environ=env)

    report = {
        "adapter": "dcc-mcp-resolve",
        "transport": chosen,
        "transport_env_var": ENV_VAR,
        "target_resolve_version": TARGET_VERSION,
        "host_version": version,
        "host_product_name": product,
        "host_edition": edition,
        "host_available": host is not None,
        "transport_error": transport_error,
        "host_version_supported": is_supported(version) if version else None,
        "scripting_dirs_found": script_dirs,
        "scripting_library_found": _library_present(environ=env),
        "script_api_env_var": SCRIPT_API_ENV,
        "script_lib_env_var": SCRIPT_LIB_ENV,
        "python_version": platform.python_version(),
        "python_bitness_ok": sys.maxsize > 2**32,
        "notes": [],
    }

    if transport_error:
        report["notes"].append("Transport misconfigured: %s" % transport_error)
    elif not report["host_available"]:
        report["notes"].append("DaVinci Resolve is not reachable over the selected transport.")
        if chosen != IN_PROCESS and not script_dirs:
            report["notes"].append(
                "No Resolve scripting directory was found; set %s to the Developer/Scripting "
                "directory." % SCRIPT_API_ENV
            )
    if not report["python_bitness_ok"]:
        report["notes"].append("The Resolve scripting API requires a 64-bit Python interpreter.")
    if report["host_available"] and not report["host_version_supported"]:
        report["notes"].append("The running Resolve version is outside the supported major lines (18-21).")
    if chosen != IN_PROCESS:
        report["notes"].append(
            "External scripting requires DaVinci Resolve Studio from Resolve 19.1 onward; "
            "the free edition must use the in_process transport."
        )
    report["notes"].append(
        "The current CI suite is host-free; host-side behaviour requires separate validation "
        "against a running DaVinci Resolve."
    )
    return report


def external_scripting_expected_to_work(report):
    """Whether the external transport should be able to connect.

    Returns ``None`` when the host version cannot be parsed, since the answer
    depends on a release line the adapter could not read. This is a
    compatibility-matrix statement, not proof of a live connection.
    """
    from .compat import external_scripting_allowed

    if report["host_version"] is None:
        return None
    return external_scripting_allowed(report["host_version"], report["host_product_name"])


def edition_blocks_transport(report):
    """Whether the detected edition cannot serve the report's transport.

    Returns ``False`` for anything other than the one hard case: the external
    transport against a free-edition host on a release line where external
    scripting is Studio-only.
    """
    from .compat import external_scripting_allowed

    if report["transport"] == IN_PROCESS or report["host_version"] is None:
        return False
    return external_scripting_allowed(report["host_version"], report["host_product_name"]) is False


def transport_fault_for(report):
    """A :class:`TransportConfigError` for an edition/transport mismatch.

    Returns ``None`` when the pairing is fine. Used by the doctor to convert a
    silently unreachable host into an actionable, staged failure.
    """
    if not edition_blocks_transport(report):
        return None
    return EditionNotSupportedError(
        "external scripting requires DaVinci Resolve Studio from Resolve 19.1 onward; "
        "this host reports %r. Use the in_process transport (Workspace > Scripts) on the "
        "free edition, or set %s=%s" % (report["host_product_name"], ENV_VAR, IN_PROCESS)
    )


def build_report_for(transport=None, environ=None):
    """Build a readiness report, probing both transports when useful.

    The free edition cannot answer an external connection at all, so an
    ``external`` report on a free host would look identical to "Resolve is not
    running". When the external transport finds nothing, this falls back to an
    in-process probe: if a ``resolve`` global *is* present, the host is running
    and simply refusing the external connection, which is a licensing answer
    rather than a liveness one.

    The returned report keeps the requested transport, so callers see the
    transport they asked about with the edition evidence attached.
    """
    requested = resolve_transport(transport, environ=environ)
    report = environment_report(requested, environ=environ)
    if requested != IN_PROCESS and not report["host_available"]:
        probe = environment_report(IN_PROCESS, environ=environ)
        if probe["host_available"]:
            report["host_version"] = probe["host_version"]
            report["host_product_name"] = probe["host_product_name"]
            report["host_edition"] = probe["host_edition"]
            report["host_version_supported"] = probe["host_version_supported"]
            report["transport_error"] = None
            report["notes"] = [
                "Detected through the in-process probe: this host is running but did not "
                "answer an external scripting connection.",
                "External scripting is a DaVinci Resolve Studio feature from Resolve 19.1 "
                "onward, so a free-edition host never answers it. A missing scripting "
                "directory is a different fault and is reported separately.",
            ] + probe["notes"]
    return report
