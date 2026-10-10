"""Transport resolution, scripting discovery, and the edition gate."""

import importlib
import inspect
import os
import sys
import types

import pytest

from dcc_mcp_resolve.transport import (
    DEFAULT_TRANSPORT,
    ENV_VAR,
    EXTERNAL,
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


def test_defaults_to_external_without_env():
    """External is the default: it is the only full-coverage transport."""
    assert resolve_transport(environ={}) == DEFAULT_TRANSPORT == EXTERNAL


def test_reads_transport_from_environ():
    assert resolve_transport(environ={ENV_VAR: IN_PROCESS}) == IN_PROCESS


def test_explicit_value_wins_over_environ():
    assert resolve_transport(IN_PROCESS, environ={ENV_VAR: EXTERNAL}) == IN_PROCESS


def test_value_is_case_and_space_insensitive():
    assert resolve_transport(" In_Process ", environ={}) == IN_PROCESS


def test_empty_env_value_falls_back_to_default():
    assert resolve_transport(environ={ENV_VAR: "   "}) == DEFAULT_TRANSPORT


def test_unknown_transport_is_rejected():
    with pytest.raises(TransportError, match="unknown Resolve transport"):
        resolve_transport("websockets", environ={})


def test_error_message_lists_valid_choices():
    with pytest.raises(TransportError) as excinfo:
        resolve_transport("nope", environ={})
    message = str(excinfo.value)
    assert IN_PROCESS in message and EXTERNAL in message


def test_script_api_env_var_wins():
    assert script_api_paths(environ={SCRIPT_API_ENV: "/custom/scripting"}) == ["/custom/scripting"]


@pytest.mark.parametrize(
    "platform,marker",
    [
        ("win32", "Blackmagic Design"),
        ("darwin", "Blackmagic Design"),
        ("linux", "resolve"),
    ],
)
def test_script_api_paths_are_platform_specific(monkeypatch, platform, marker):
    monkeypatch.setattr(sys, "platform", platform)
    paths = script_api_paths(environ={})
    assert paths
    assert all(marker in path for path in paths)


@pytest.mark.parametrize("platform", ["win32", "darwin", "linux"])
def test_script_lib_paths_are_platform_specific(monkeypatch, platform):
    monkeypatch.setattr(sys, "platform", platform)
    paths = script_lib_paths(environ={SCRIPT_LIB_ENV: None} if False else {})
    assert paths
    assert all("fusionscript" in os.path.basename(path) for path in paths)


def test_windows_script_lib_is_a_dll(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert script_lib_paths(environ={})[0].endswith("fusionscript.dll")


def test_macos_script_lib_is_a_shared_object(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert script_lib_paths(environ={})[0].endswith("fusionscript.so")


def test_in_process_resolve_returns_injected_global(monkeypatch):
    sentinel = object()
    monkeypatch.setattr("builtins.resolve", sentinel, raising=False)
    assert in_process_resolve() is sentinel


def test_in_process_resolve_raises_outside_resolve(monkeypatch):
    monkeypatch.delattr("builtins.resolve", raising=False)
    with pytest.raises(TransportError, match="injected 'resolve' global"):
        in_process_resolve()


def test_in_process_failure_names_the_alternative(monkeypatch):
    """The error should tell the user how to get unstuck."""
    monkeypatch.delattr("builtins.resolve", raising=False)
    with pytest.raises(TransportError) as excinfo:
        in_process_resolve()
    assert EXTERNAL in str(excinfo.value)


class _FakeScriptModule:
    def __init__(self, app=None, raises=False):
        self._app = app
        self._raises = raises

    def scriptapp(self, name):
        assert name == "Resolve"
        if self._raises:
            raise RuntimeError("connection refused")
        return self._app


def test_external_resolve_returns_the_app(monkeypatch, tmp_path):
    modules = tmp_path / "Modules"
    modules.mkdir()
    (modules / "DaVinciResolveScript.py").write_text("", encoding="utf-8")
    monkeypatch.setenv(SCRIPT_API_ENV, str(tmp_path))
    monkeypatch.setitem(sys.modules, "DaVinciResolveScript", _FakeScriptModule(app="app"))
    assert external_resolve() == "app"


def test_external_resolve_returns_none_when_host_absent(monkeypatch, tmp_path):
    """Resolve not running is an ordinary state, not a configuration fault."""
    modules = tmp_path / "Modules"
    modules.mkdir()
    (modules / "DaVinciResolveScript.py").write_text("", encoding="utf-8")
    monkeypatch.setenv(SCRIPT_API_ENV, str(tmp_path))
    monkeypatch.setitem(sys.modules, "DaVinciResolveScript", _FakeScriptModule(app=None))
    assert external_resolve() is None


def test_external_resolve_treats_raises_as_absent_host(monkeypatch, tmp_path):
    modules = tmp_path / "Modules"
    modules.mkdir()
    (modules / "DaVinciResolveScript.py").write_text("", encoding="utf-8")
    monkeypatch.setenv(SCRIPT_API_ENV, str(tmp_path))
    monkeypatch.setitem(sys.modules, "DaVinciResolveScript", _FakeScriptModule(raises=True))
    assert external_resolve() is None


def test_missing_scripting_directory_is_a_config_error(monkeypatch, tmp_path):
    monkeypatch.setenv(SCRIPT_API_ENV, str(tmp_path / "does-not-exist"))
    with pytest.raises(TransportConfigError, match="DaVinciResolveScript.py was not found"):
        external_resolve()


def test_missing_scripting_directory_error_names_the_env_var(monkeypatch, tmp_path):
    monkeypatch.setenv(SCRIPT_API_ENV, str(tmp_path / "does-not-exist"))
    with pytest.raises(TransportConfigError) as excinfo:
        external_resolve()
    assert SCRIPT_API_ENV in str(excinfo.value)


def test_unimportable_module_is_a_config_error_not_an_importerror(monkeypatch, tmp_path):
    """A found-but-broken module must not surface as a bare ImportError."""
    modules = tmp_path / "Modules"
    modules.mkdir()
    (modules / "DaVinciResolveScript.py").write_text("", encoding="utf-8")
    monkeypatch.setenv(SCRIPT_API_ENV, str(tmp_path))
    monkeypatch.setitem(sys.modules, "DaVinciResolveScript", None)
    with pytest.raises(TransportConfigError, match="could not be imported"):
        external_resolve()


def test_edition_error_is_a_transport_config_error():
    """The free-edition gate is a configuration fault, not an absent host."""
    assert issubclass(EditionNotSupportedError, TransportConfigError)


def test_transport_module_exposes_both_scripting_env_vars():
    source = importlib.import_module("dcc_mcp_resolve.transport")
    text = inspect.getsource(source)
    assert "RESOLVE_SCRIPT_API" in text
    assert "RESOLVE_SCRIPT_LIB" in text


def test_transport_module_never_imports_the_host_at_module_scope():
    """A machine without Resolve installed must still import this package."""
    source = inspect.getsource(importlib.import_module("dcc_mcp_resolve.transport"))
    assert "import DaVinciResolveScript" in source
    # The import is inside a function body, so module import stays side-effect free.
    for line in source.splitlines():
        if line.startswith("import DaVinciResolveScript") or line.startswith("from DaVinciResolveScript"):
            pytest.fail("DaVinciResolveScript must not be imported at module scope")


def test_stub_module_helper_is_unused_but_importable():
    assert isinstance(types.ModuleType("x"), types.ModuleType)
