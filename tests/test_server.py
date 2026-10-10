"""Server construction: the two transports have different binding rules."""

import pytest

from dcc_mcp_resolve.server import ResolveServer
from dcc_mcp_resolve.transport import EXTERNAL, IN_PROCESS


def test_in_process_requires_a_host_pid():
    with pytest.raises(ValueError, match="requires the Resolve host PID"):
        ResolveServer(port=0, dcc_pid=None, transport=IN_PROCESS)


def test_external_rejects_a_host_pid():
    with pytest.raises(ValueError, match="only valid for the in_process"):
        ResolveServer(port=0, dcc_pid=1234, transport=EXTERNAL)


def test_external_transport_constructs():
    server = ResolveServer(port=0, dcc_pid=None, transport=EXTERNAL)
    assert server.transport == EXTERNAL


def test_in_process_preserves_supplied_host_dispatcher():
    dispatcher = object()
    server = ResolveServer(
        port=0,
        dcc_pid=1234,
        transport=IN_PROCESS,
        dispatcher=dispatcher,
        enable_file_logging=False,
        enable_job_persistence=False,
    )
    assert server.transport == IN_PROCESS
    assert server._execution_bridge.dispatcher is dispatcher
    assert server._dcc_dispatcher is dispatcher
