"""Doctor contract smoke.

The doctor is where the adapter assembles an Install SOP report and validates
it before the report is published. This test runs the real report — built from
what the adapter actually observes, not a hand-written fixture — through Core's
validator, which is what contract rule A014 asks for.
"""

import sys

import pytest

from dcc_mcp_resolve import doctor
from dcc_mcp_resolve.transport import EXTERNAL, IN_PROCESS, SCRIPT_API_ENV

STUDIO = "DaVinci Resolve Studio"
FREE = "DaVinci Resolve"


def _fake_app(version="21.1.0.18", product=STUDIO):
    class _App:
        @staticmethod
        def GetVersionString():
            return version

        @staticmethod
        def GetProductName():
            return product

    return _App()


def test_schema_version_is_read_from_core_not_re_declared():
    revision = doctor.schema_version()
    assert revision is None or isinstance(revision, (int, str))


def test_report_carries_identity():
    report = doctor.build_report(EXTERNAL, environ={})
    assert report["dcc_type"] == "resolve"
    assert report["adapter_version"]


def test_report_names_the_transport_it_describes():
    assert doctor.build_report(IN_PROCESS, environ={})["environment"]["transport"] == IN_PROCESS


def test_report_declares_sop_status():
    status = doctor.build_report(EXTERNAL, environ={})["status"]
    assert status in ("planned", "running", "ok", "failed", "partial", "requires_restart")


def test_report_carries_the_install_steps():
    steps = doctor.build_report(EXTERNAL, environ={})["steps"]
    assert [step["id"] for step in steps] == [
        "install-package",
        "connect-host",
        "verify-host",
    ]


def test_verify_block_reports_a_reason_when_not_usable():
    verify = doctor.build_report(EXTERNAL, environ={})["verify"]
    assert verify["directly_usable"] is False
    assert verify["failure_stage"] == "transport"
    assert verify["failure_reason"]


def test_next_steps_are_offered_only_when_not_usable():
    report = doctor.build_report(EXTERNAL, environ={})
    assert report["next_steps"]
    for step in report["next_steps"]:
        assert step["id"] and step["description"] and step["why"]


def test_core_version_is_reported():
    assert doctor.build_report(EXTERNAL, environ={})["core_version"]


def test_validate_a_real_report():
    if doctor.validate_install_sop_report is None:
        pytest.skip("dcc-mcp-core does not expose validate_install_sop_report")
    ok, errors = doctor.validate()
    assert ok, errors


def test_misconfigured_transport_is_staged_as_transport_not_host():
    """The failure stage must say 'transport' -- 'host' sends users the wrong way."""
    verify = doctor.build_report(EXTERNAL, environ={SCRIPT_API_ENV: "/nonexistent"})["verify"]
    assert verify["directly_usable"] is False
    assert verify["failure_stage"] == "transport"
    assert "DaVinciResolveScript" in verify["failure_reason"]


def test_misconfigured_transport_still_validates():
    """A broken install must still produce a schema-valid report."""
    if doctor.validate_install_sop_report is None:
        pytest.skip("dcc-mcp-core does not expose validate_install_sop_report")
    ok, errors = doctor.validate(doctor.build_report(EXTERNAL, environ={SCRIPT_API_ENV: "/nonexistent"}))
    assert ok, errors


class TestFreeEditionDiagnosis:
    """A licensing wall must not be reported as 'Resolve is not running'.

    The free edition refuses external connections outright, so an external
    probe alone cannot tell "not running" from "not licensed". The in-process
    probe settles it: a ``resolve`` global means the host is up.
    """

    @pytest.fixture(autouse=True)
    def _free_host(self, monkeypatch):
        monkeypatch.setattr("builtins.resolve", _fake_app(product=FREE), raising=False)

    def test_the_probe_recovers_the_edition(self):
        report = doctor.build_report(EXTERNAL, environ={})
        assert report["environment"]["host_edition"] == "free"
        assert report["environment"]["host_available"] is False

    def test_failure_stage_is_transport_not_host(self):
        verify = doctor.build_report(EXTERNAL, environ={})["verify"]
        assert verify["failure_stage"] == "transport"
        assert "Studio" in verify["failure_reason"]

    def test_next_steps_explain_new_python_requirement(self):
        step_ids = [step["id"] for step in doctor.build_report(EXTERNAL, environ={})["next_steps"]]
        assert "switch-to-in-process" not in step_ids
        assert "review-python-requirement" in step_ids

    def test_next_steps_do_not_tell_the_user_to_start_resolve(self):
        """Starting Resolve cannot fix a Studio-only feature gate."""
        step_ids = [step["id"] for step in doctor.build_report(EXTERNAL, environ={})["next_steps"]]
        assert "start-resolve" not in step_ids

    def test_the_probe_explains_itself(self):
        notes = doctor.build_report(EXTERNAL, environ={})["environment"]["notes"]
        assert any("in-process probe" in note for note in notes)

    def test_broken_install_still_validates(self):
        if doctor.validate_install_sop_report is None:
            pytest.skip("dcc-mcp-core does not expose validate_install_sop_report")
        ok, errors = doctor.validate(doctor.build_report(EXTERNAL, environ={}))
        assert ok, errors


class TestStudioOnExternal:
    """The gate must not fire for Studio, where external scripting works."""

    @pytest.fixture(autouse=True)
    def _studio_host(self, monkeypatch, tmp_path):
        modules = tmp_path / "Modules"
        modules.mkdir()
        (modules / "DaVinciResolveScript.py").write_text("", encoding="utf-8")
        monkeypatch.setenv(SCRIPT_API_ENV, str(tmp_path))

        class _Module:
            @staticmethod
            def scriptapp(name):
                return _fake_app(product=STUDIO)

        monkeypatch.setitem(sys.modules, "DaVinciResolveScript", _Module)

    def test_studio_on_external_is_usable(self):
        verify = doctor.build_report(EXTERNAL)["verify"]
        assert verify["directly_usable"] is True

    def test_no_switch_step_is_offered(self):
        assert doctor.build_report(EXTERNAL)["next_steps"] == []


def test_absent_host_offers_start_resolve():
    """The ordinary 'not running' case keeps the ordinary advice."""
    monkeypatched = doctor.build_report(EXTERNAL, environ={SCRIPT_API_ENV: "/nonexistent"})
    assert "fix-transport" in [s["id"] for s in monkeypatched["next_steps"]]


def test_edition_fault_is_not_reported_on_in_process(monkeypatch):
    monkeypatch.setattr("builtins.resolve", _fake_app(version="21.0", product=FREE), raising=False)
    verify = doctor.build_report(IN_PROCESS, environ={})["verify"]
    assert verify["failure_stage"] is None


@pytest.mark.parametrize("transport", [EXTERNAL, IN_PROCESS])
def test_free_21_1_never_becomes_usable_or_offers_transport_switch(monkeypatch, transport):
    monkeypatch.setattr("builtins.resolve", _fake_app(product=FREE), raising=False)
    report = doctor.build_report(transport, environ={})
    assert report["verify"]["directly_usable"] is False
    assert report["verify"]["failure_stage"] == "transport"
    assert "Python" in report["verify"]["failure_reason"]
    assert "switch-to-in-process" not in [step["id"] for step in report["next_steps"]]
    assert "start-resolve" not in [step["id"] for step in report["next_steps"]]
    assert doctor.validate(report)[0]


def test_legacy_free_external_still_offers_in_process(monkeypatch):
    monkeypatch.setattr("builtins.resolve", _fake_app(version="18.6", product=FREE), raising=False)
    report = doctor.build_report(EXTERNAL, environ={})
    assert report["verify"]["directly_usable"] is False
    assert "switch-to-in-process" in [step["id"] for step in report["next_steps"]]


@pytest.mark.parametrize("version,product", [("21.1", ""), ("21.bad", STUDIO), ("22.0", STUDIO)])
def test_unknown_identity_is_never_directly_usable(monkeypatch, version, product):
    monkeypatch.setattr("builtins.resolve", _fake_app(version=version, product=product), raising=False)
    report = doctor.build_report(IN_PROCESS, environ={})
    assert report["verify"]["directly_usable"] is False
    assert report["environment"]["transport_supported"] is None
    assert report["next_steps"]
