"""Readiness reporting never raises when Resolve is absent."""

import json
import sys

import pytest

from dcc_mcp_resolve.runtime import (
    detect_host,
    detect_host_version,
    edition_blocks_transport,
    environment_report,
    external_scripting_expected_to_work,
    transport_fault_for,
)
from dcc_mcp_resolve.transport import (
    EXTERNAL,
    IN_PROCESS,
    SCRIPT_API_ENV,
    EditionNotSupportedError,
    TransportConfigError,
)

STUDIO = "DaVinci Resolve Studio"
FREE = "DaVinci Resolve"


def _install_fake_scripting(monkeypatch, tmp_path, app):
    """Point the adapter at a fake scripting dir wired to ``app``."""
    modules = tmp_path / "Modules"
    modules.mkdir()
    (modules / "DaVinciResolveScript.py").write_text("", encoding="utf-8")
    monkeypatch.setenv(SCRIPT_API_ENV, str(tmp_path))

    class _Module:
        @staticmethod
        def scriptapp(name):
            return app

    monkeypatch.setitem(sys.modules, "DaVinciResolveScript", _Module)


def _fake_app(version="21.1.0.18", product=STUDIO):
    class _App:
        @staticmethod
        def GetVersionString():
            return version

        @staticmethod
        def GetProductName():
            return product

    return _App()


def test_report_is_json_serialisable():
    report = environment_report(EXTERNAL, environ={})
    assert json.loads(json.dumps(report)) == report


def test_report_names_the_transport():
    assert environment_report(EXTERNAL, environ={})["transport"] == EXTERNAL
    assert environment_report(IN_PROCESS, environ={})["transport"] == IN_PROCESS


def test_absent_host_is_reported_not_raised():
    report = environment_report(EXTERNAL, environ={SCRIPT_API_ENV: "/nonexistent-scripting"})
    assert report["host_available"] is False
    assert report["host_version"] is None


def test_absent_host_still_lists_what_was_searched():
    report = environment_report(EXTERNAL, environ={})
    assert isinstance(report["scripting_dirs_found"], list)
    assert isinstance(report["scripting_library_found"], bool)


class TestHostAbsent:
    """Resolve installed and configured, but not running.

    This is the case that must read as an ordinary absent host rather than a
    broken install: the scripting directory exists, ``scriptapp`` simply
    declines to hand back an application.
    """

    @pytest.fixture(autouse=True)
    def _wired_but_not_running(self, monkeypatch, tmp_path):
        modules = tmp_path / "Modules"
        modules.mkdir()
        (modules / "DaVinciResolveScript.py").write_text("", encoding="utf-8")
        monkeypatch.setenv(SCRIPT_API_ENV, str(tmp_path))

        class _Module:
            @staticmethod
            def scriptapp(name):
                return None

        monkeypatch.setitem(sys.modules, "DaVinciResolveScript", _Module)

    def test_host_is_unavailable(self):
        assert environment_report(EXTERNAL)["host_available"] is False

    def test_no_transport_error_is_reported(self):
        assert environment_report(EXTERNAL)["transport_error"] is None

    def test_a_note_explains_the_host_is_not_reachable(self):
        assert any("not reachable" in note for note in environment_report(EXTERNAL)["notes"])


def test_report_always_states_ci_does_not_cover_the_host():
    notes = environment_report(EXTERNAL, environ={})["notes"]
    assert any("CI suite is host-free" in note for note in notes)


def test_report_states_the_studio_requirement_on_external():
    notes = environment_report(EXTERNAL, environ={})["notes"]
    assert any("Studio" in note for note in notes)


def test_report_does_not_claim_studio_requirement_on_in_process():
    notes = environment_report(IN_PROCESS, environ={})["notes"]
    assert not any("Studio" in note for note in notes)


class TestHostDetected:
    @pytest.fixture(autouse=True)
    def _wired(self, monkeypatch, tmp_path):
        _install_fake_scripting(monkeypatch, tmp_path, _fake_app())

    def test_studio_host_is_reachable(self):
        report = environment_report(EXTERNAL)
        assert report["host_available"] is True
        assert report["host_version"] == "21.1.0.18"
        assert report["host_edition"] == "studio"

    def test_studio_host_has_no_transport_error(self):
        assert environment_report(EXTERNAL)["transport_error"] is None

    def test_detect_host_version_reads_the_host(self):
        assert detect_host_version(EXTERNAL) == "21.1.0.18"

    def test_detect_host_returns_version_and_product(self):
        assert detect_host(EXTERNAL) == {"version": "21.1.0.18", "product": STUDIO}

    def test_no_edition_fault_for_studio_on_external(self):
        report = environment_report(EXTERNAL)
        assert edition_blocks_transport(report) is False
        assert transport_fault_for(report) is None

    def test_studio_allows_external_scripting(self):
        assert external_scripting_expected_to_work(environment_report(EXTERNAL)) is True


class TestFreeEditionGate:
    """The one diagnosis the adapter must not get wrong.

    The free edition refuses external connections from Resolve 19.1 onward, so
    ``host_available`` is false for a licensing reason. Reporting that as an
    absent host would tell the user to start Resolve, which cannot help.
    """

    @pytest.fixture(autouse=True)
    def _wired(self, monkeypatch, tmp_path):
        _install_fake_scripting(monkeypatch, tmp_path, None)

    def _report_with(self, monkeypatch, tmp_path, app):
        _install_fake_scripting(monkeypatch, tmp_path, app)
        return environment_report(EXTERNAL)

    def test_free_edition_on_external_is_blocked(self, monkeypatch, tmp_path):
        # A free host cannot be reached externally, so it looks absent; seed the
        # report from a reachable in-process read to model the detected edition.
        report = environment_report(IN_PROCESS)
        monkeypatch.setattr("builtins.resolve", _fake_app(product=FREE), raising=False)
        report = environment_report(IN_PROCESS)
        report["transport"] = EXTERNAL
        assert edition_blocks_transport(report) is True

    def test_fault_is_an_edition_error(self, monkeypatch):
        monkeypatch.setattr("builtins.resolve", _fake_app(product=FREE), raising=False)
        report = environment_report(IN_PROCESS)
        report["transport"] = EXTERNAL
        fault = transport_fault_for(report)
        assert isinstance(fault, EditionNotSupportedError)

    def test_fault_message_names_studio_and_the_alternative(self, monkeypatch):
        monkeypatch.setattr("builtins.resolve", _fake_app(product=FREE), raising=False)
        report = environment_report(IN_PROCESS)
        report["transport"] = EXTERNAL
        message = str(transport_fault_for(report))
        assert "Studio" in message
        assert IN_PROCESS in message

    def test_free_edition_on_in_process_is_not_blocked(self, monkeypatch):
        monkeypatch.setattr("builtins.resolve", _fake_app(product=FREE), raising=False)
        report = environment_report(IN_PROCESS)
        assert edition_blocks_transport(report) is False
        assert transport_fault_for(report) is None

    def test_unknown_version_is_not_treated_as_blocked(self):
        report = environment_report(EXTERNAL, environ={})
        report["host_version"] = ""
        assert edition_blocks_transport(report) is False


class TestTransportMisconfiguration:
    @pytest.fixture(autouse=True)
    def _broken(self, monkeypatch):
        monkeypatch.setenv(SCRIPT_API_ENV, "/nonexistent-scripting")

    def test_detect_host_raises_instead_of_returning_none(self):
        with pytest.raises(TransportConfigError):
            detect_host(EXTERNAL)

    def test_report_carries_the_transport_error(self):
        report = environment_report(EXTERNAL, environ={SCRIPT_API_ENV: "/nonexistent-scripting"})
        assert report["transport_error"]
        assert "DaVinciResolveScript" in report["transport_error"]

    def test_report_does_not_blame_the_absent_host(self):
        notes = environment_report(EXTERNAL, environ={SCRIPT_API_ENV: "/nonexistent-scripting"})["notes"]
        assert not any("not reachable" in note for note in notes)
        assert any("misconfigured" in note.lower() for note in notes)

    def test_report_stays_serialisable(self):
        report = environment_report(EXTERNAL, environ={SCRIPT_API_ENV: "/nonexistent-scripting"})
        assert json.loads(json.dumps(report)) == report


def test_in_process_host_is_read_from_the_injected_global(monkeypatch):
    monkeypatch.setattr("builtins.resolve", _fake_app(version="21.0", product=FREE), raising=False)
    report = environment_report(IN_PROCESS, environ={})
    assert report["host_available"] is True
    assert report["host_edition"] == "free"


def test_unsupported_version_is_reported(monkeypatch, tmp_path):
    _install_fake_scripting(monkeypatch, tmp_path, _fake_app(version="17.4"))
    report = environment_report(EXTERNAL)
    assert report["host_version_supported"] is False
    assert any("outside the supported" in note for note in report["notes"])
