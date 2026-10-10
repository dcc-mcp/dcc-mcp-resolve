"""Transport selection for the DaVinci Resolve adapter.

Resolve is reachable over two materially different channels, and which one is
in use decides what the adapter can do. The split is not a convenience choice:
it is forced by Resolve's own licensing.

``external``
    The adapter runs in its own process and connects to a running Resolve over
    the external scripting socket exposed by ``DaVinciResolveScript.scriptapp``.
    This is the primary path and the only one with full read coverage, but
    **since roughly Resolve 19.1, external scripting is a Studio-only
    feature** -- the free edition refuses connections from another process.
    It needs ``RESOLVE_SCRIPT_API`` and ``RESOLVE_SCRIPT_LIB`` to point at the
    installed Developer/Scripting directory and the fusionscript library.

``in_process``
    The adapter runs *inside* Resolve as a script launched from the
    ``Workspace > Scripts`` menu, where a ``resolve`` global is injected. This
    is the only path available on the free edition. It cannot reach every
    surface: in-app scripts do not cover render/deliver jobs or the color page
    in the same way the external API does, and it needs a human to click the
    script.

The choice is data-driven from ``DCC_MCP_RESOLVE_TRANSPORT`` so tests and CI can
exercise both paths without a live host. See ``docs/adr/0001-transport.md``.

Note on Python coupling: the scripting API is documented against Python >= 3.6
64-bit, but Resolve also ships its own interpreter (ResolvePython 3.14 in 21.1)
and community practice clusters on 3.9-3.11. Nothing here imports a host module
at import time -- every access goes through the accessors below so that a
machine without Resolve installed can still import, install and doctor this
package.
"""

IN_PROCESS = "in_process"
EXTERNAL = "external"

TRANSPORTS = (IN_PROCESS, EXTERNAL)

DEFAULT_TRANSPORT = EXTERNAL

ENV_VAR = "DCC_MCP_RESOLVE_TRANSPORT"

SCRIPT_API_ENV = "RESOLVE_SCRIPT_API"

SCRIPT_LIB_ENV = "RESOLVE_SCRIPT_LIB"


class TransportError(RuntimeError):
    """Raised when a transport is requested but cannot be honoured."""


class TransportConfigError(TransportError):
    """The selected transport is installed or configured incorrectly.

    Distinct from the host merely being unreachable: Resolve not running is an
    expected state that readiness reporting should describe, whereas a scripting
    install the adapter cannot find -- or an edition that refuses external
    scripting -- is a fault the user must fix.
    """


class EditionNotSupportedError(TransportConfigError):
    """The detected Resolve edition cannot serve the requested transport.

    Raised specifically for the free-edition-on-external-transport case, which
    is the one configuration failure a user cannot fix by installing anything.
    """


def resolve_transport(value=None, environ=None):
    """Return the transport name to use.

    ``value`` wins when given; otherwise ``DCC_MCP_RESOLVE_TRANSPORT`` is read
    from ``environ`` (defaulting to ``os.environ``). An empty or unset value
    falls back to :data:`DEFAULT_TRANSPORT`. Unknown values are rejected rather
    than silently downgraded, because a typo should not look like a working
    external setup.
    """
    import os

    chosen = value
    if chosen is None:
        chosen = (environ if environ is not None else os.environ).get(ENV_VAR)
    if chosen is None or not str(chosen).strip():
        return DEFAULT_TRANSPORT
    chosen = str(chosen).strip().lower()
    if chosen not in TRANSPORTS:
        raise TransportError("unknown Resolve transport %r; expected one of %s" % (chosen, ", ".join(TRANSPORTS)))
    return chosen


def script_api_paths(environ=None):
    """Candidate Developer/Scripting directories for this platform.

    ``RESOLVE_SCRIPT_API`` always wins when set. Otherwise the documented
    per-platform defaults are offered. Returning every candidate rather than a
    single path is deliberate: the doctor can then report which ones exist,
    which is what makes a missing-install diagnosis actionable.
    """
    import os

    env = environ if environ is not None else os.environ
    explicit = env.get(SCRIPT_API_ENV)
    if explicit:
        return [explicit]

    import sys

    if sys.platform.startswith("win"):
        program_data = env.get("PROGRAMDATA") or r"C:\ProgramData"
        return [
            r"%s\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting" % program_data,
            r"%LOCALAPPDATA%\Programs\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting",
        ]
    if sys.platform == "darwin":
        return [
            "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting",
            (
                "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Resources/"
                "Blackmagic Design/DaVinci Resolve/Developer/Scripting"
            ),
        ]
    return ["/opt/resolve/Developer/Scripting", "/home/resolve/Developer/Scripting"]


def script_lib_paths(environ=None):
    """Candidate paths to the ``fusionscript`` shared library."""
    import os
    import sys

    env = environ if environ is not None else os.environ
    explicit = env.get(SCRIPT_LIB_ENV)
    if explicit:
        return [explicit]

    if sys.platform.startswith("win"):
        program_files = env.get("PROGRAMFILES") or r"C:\Program Files"
        return [
            r"%s\Blackmagic Design\DaVinci Resolve\fusionscript.dll" % program_files,
        ]
    if sys.platform == "darwin":
        return [
            "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so",
        ]
    return ["/opt/resolve/libs/Fusion/fusionscript.so"]


def resolve_script_module(environ=None):
    """Import and return the ``DaVinciResolveScript`` module.

    The module is not importable by default: it lives in
    ``$RESOLVE_SCRIPT_API/Modules``, which is never on ``sys.path``. This
    helper adds the first candidate directory that actually contains the module
    and imports it, so the failure mode for a missing install is one clear
    :class:`TransportConfigError` instead of a bare ``ImportError``.

    Raises :class:`TransportConfigError` when no candidate directory holds the
    module.
    """
    import os
    import sys

    env = environ if environ is not None else os.environ
    for candidate in script_api_paths(environ=env):
        modules = os.path.join(candidate, "Modules")
        if not os.path.isfile(os.path.join(modules, "DaVinciResolveScript.py")):
            continue
        if modules not in sys.path:
            sys.path.insert(0, modules)
        try:
            import DaVinciResolveScript  # type: ignore[import-not-found]
        except ImportError as exc:
            raise TransportConfigError(
                "found DaVinciResolveScript.py under %s but it could not be imported: %s" % (modules, exc)
            ) from exc
        return DaVinciResolveScript
    raise TransportConfigError(
        "DaVinciResolveScript.py was not found under any scripting directory; "
        "set %s to Resolve's Developer/Scripting directory (tried: %s)"
        % (SCRIPT_API_ENV, ", ".join(script_api_paths(environ=env)))
    )


def external_resolve(environ=None):
    """Connect to a running Resolve over external scripting and return the app.

    Returns ``None`` when ``scriptapp("Resolve")`` declines to hand back an
    object, which is how the API reports "Resolve is not running" (as opposed
    to "scripting is not installed", which raises).
    """
    module = resolve_script_module(environ=environ)
    try:
        return module.scriptapp("Resolve")
    except Exception:
        # scriptapp raises rather than returning None on some builds when the
        # host is absent; both shapes mean the same thing to the caller.
        return None


def in_process_resolve():
    """Return the ``resolve`` global Resolve injects into in-app scripts.

    Raises :class:`TransportError` when no such global exists, so callers get
    one explicit failure instead of a ``NameError``.
    """
    import builtins

    app = getattr(builtins, "resolve", None)
    if app is None:
        raise TransportError(
            "in_process transport requires Resolve's injected 'resolve' global; "
            "run this adapter from Workspace > Scripts, or set %s=%s" % (ENV_VAR, EXTERNAL)
        )
    return app


def resolve_app(transport=None, environ=None):
    """Return the live Resolve application object for the given transport."""
    chosen = resolve_transport(transport, environ=environ)
    if chosen == IN_PROCESS:
        return in_process_resolve()
    return external_resolve(environ=environ)
