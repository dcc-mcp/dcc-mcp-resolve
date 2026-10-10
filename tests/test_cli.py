"""CLI surface: doctor prints JSON, serve validates its transport arguments."""

import json
from unittest.mock import Mock, call

import pytest

from dcc_mcp_resolve.cli import main


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert capsys.readouterr().out.strip()


def test_doctor_prints_json(capsys):
    assert main(["doctor"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["adapter"] == "dcc-mcp-resolve"
    assert "transport" in report


def test_serve_requires_a_pid_for_in_process(capsys):
    with pytest.raises(SystemExit):
        main(["serve", "--transport", "in_process"])
    assert "--pid is required" in capsys.readouterr().err


def test_serve_rejects_a_pid_for_external(capsys):
    with pytest.raises(SystemExit):
        main(["serve", "--transport", "external", "--pid", "1234"])
    assert "only valid for the in_process" in capsys.readouterr().err


def test_no_command_prints_help(capsys):
    assert main([]) == 1
    assert "usage" in capsys.readouterr().out.lower()


@pytest.mark.parametrize("registration_fails", [False, True])
def test_serve_registers_skills_and_always_stops(registration_fails, monkeypatch, capsys):
    server = Mock(mcp_url="http://127.0.0.1:1234/mcp", instance_id="test-resolve")
    factory = Mock(return_value=server)
    stopped = Mock()
    stopped.wait.return_value = True
    monkeypatch.setattr("dcc_mcp_resolve.server.ResolveServer", factory)
    monkeypatch.setattr("dcc_mcp_resolve.cli.threading.Event", lambda: stopped)
    monkeypatch.setattr("dcc_mcp_resolve.cli.signal.signal", lambda *args: None)
    if registration_fails:
        server.register_builtin_actions.side_effect = RuntimeError("skill registration failed")
        with pytest.raises(RuntimeError, match="skill registration failed"):
            main(["serve", "--transport", "external", "--port", "1234"])
        assert capsys.readouterr().out == ""
        stopped.wait.assert_not_called()
    else:
        assert main(["serve", "--transport", "external", "--port", "1234"]) == 0
        assert json.loads(capsys.readouterr().out) == {
            "mcp_url": server.mcp_url,
            "instance_id": server.instance_id,
            "transport": "external",
        }
        stopped.wait.assert_called_once_with(1)
    factory.assert_called_once_with(port=1234, dcc_pid=None, dcc_version=None, transport="external")
    assert server.mock_calls == [call.start(), call.register_builtin_actions(), call.stop()]
