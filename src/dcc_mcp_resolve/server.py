"""Composition root using core lifecycle, discovery and execution dispatch."""

from pathlib import Path

from dcc_mcp_core import DccServerBase, DccServerOptions, HostExecutionBridge

from . import __version__
from .transport import IN_PROCESS, resolve_transport


class ResolveServer(DccServerBase):
    """MCP service for one DaVinci Resolve instance.

    This server connects to a running Resolve host in one of two shapes:

    ``external``
        Started as a standalone service that connects to Resolve over the
        external scripting socket. No host PID is bound, because the adapter
        process owns its own lifetime and Resolve may restart independently.
        Requires DaVinci Resolve Studio.

    ``in_process``
        Started from a script inside Resolve's ``Workspace > Scripts`` menu,
        where the ``resolve`` global is injected. The host PID is the Resolve
        process and host API calls are dispatched onto Resolve's own thread.
        This is a legacy free-edition path before 21.1 only.
    """

    def __init__(self, port=None, dcc_pid=None, dcc_version=None, transport=None, dispatcher=None, **kwargs):
        chosen = resolve_transport(transport)
        if chosen == IN_PROCESS and dcc_pid is None:
            raise ValueError("in_process transport requires the Resolve host PID")
        if chosen != IN_PROCESS and dcc_pid is not None:
            raise ValueError("dcc_pid is only valid for the in_process transport")
        options = DccServerOptions.from_env(
            "resolve",
            Path(__file__).parent / "skills",
            port=port,
            server_name="dcc-mcp-resolve",
            adapter_version=__version__,
            instance_type="gui" if dcc_pid is not None else "standalone",
            dcc_pid=dcc_pid,
            dcc_version=dcc_version,
            execution_bridge=HostExecutionBridge(dispatcher=dispatcher),
            **kwargs,
        )
        super().__init__(options=options)
        self.transport = chosen

    def _version_string(self):
        return "unknown"
