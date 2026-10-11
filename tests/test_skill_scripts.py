"""Run bundled inspection entry points against hermetic Resolve app doubles.

No DaVinci Resolve, no license and no GUI are involved. Each script is executed
with a fake ``resolve`` global or a fake ``DaVinciResolveScript`` module, so the
tests exercise the real adapter code path that a live host would take.
"""

import json
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from dcc_mcp_resolve.transport import ENV_VAR, EXTERNAL, IN_PROCESS, SCRIPT_API_ENV

SKILLS_DIR = Path(__file__).resolve().parents[1] / "src" / "dcc_mcp_resolve" / "skills"
SCRIPTS = {
    "session_info": "resolve-session",
    "list_projects": "resolve-session",
    "project_info": "resolve-project",
    "list_media_pool": "resolve-media-pool",
    "list_folder_clips": "resolve-media-pool",
    "list_timelines": "resolve-timeline",
    "timeline_info": "resolve-timeline",
    "list_timeline_items": "resolve-timeline",
    "list_gallery_albums": "resolve-gallery",
    "list_gallery_stills": "resolve-gallery",
}

MEDIA_POOL_ITEM = SimpleNamespace(
    GetName=lambda: "A001C001.mov",
    GetClipProperty=lambda key: {
        "File Path": "/media/A001C001.mov",
        "Resolution": "1920x1080",
        "Frames": "240",
        "Frame Rate": "24",
        "Type": "Video",
    }.get(key, ""),
)
TIMELINE_ITEM = SimpleNamespace(
    GetName=lambda: "Shot 010",
    GetDuration=lambda: 240,
    GetStart=lambda: 86400,
    GetEnd=lambda: 86640,
    GetMediaPoolItem=lambda: MEDIA_POOL_ITEM,
)
STILL = SimpleNamespace(GetLabel=lambda: "Teal & Orange", GetFilePath=lambda: "/gallery/teal.png")


def _folder(name="Master", subfolders=(), clips=()):
    return SimpleNamespace(
        GetName=lambda: name,
        GetSubFolderList=lambda: list(subfolders),
        GetClipList=lambda: list(clips),
    )


def _timeline(name="Timeline 1"):
    return SimpleNamespace(
        GetName=lambda: name,
        GetStartFrame=lambda: 86400,
        GetEndFrame=lambda: 86640,
        GetStartTimecode=lambda: "01:00:00:00",
        GetTrackCount=lambda kind: {"video": 2, "audio": 3, "subtitle": 0}[kind],
        GetItemListInTrack=lambda kind, index: [TIMELINE_ITEM] if kind == "video" and index == 1 else [],
    )


def _album(name="Album 1", stills=(STILL,)):
    return SimpleNamespace(GetName=lambda: name, GetStillList=lambda: list(stills))


def _app():
    project = SimpleNamespace(
        GetName=lambda: "Demo Project",
        GetTimelineCount=lambda: 1,
        # Resolve's GetTimelineByIndex is one-based.
        GetTimelineByIndex=lambda index: _timeline() if index == 1 else None,
        GetCurrentTimeline=lambda: _timeline(),
        GetSetting=lambda key: {
            "timelineFrameRate": "24",
            "timelineResolutionWidth": "1920",
            "timelineResolutionHeight": "1080",
        }.get(key, None),
        GetMediaPool=lambda: SimpleNamespace(GetRootFolder=lambda: _folder(subfolders=[])),
        GetGallery=lambda: SimpleNamespace(GetAlbumList=lambda: [_album()]),
    )
    manager = SimpleNamespace(
        GetProjectListInCurrentFolder=lambda: ["Demo Project", "Other"],
        GetCurrentProject=lambda: project,
    )
    return SimpleNamespace(
        GetVersionString=lambda: "21.1.0.18",
        GetProductName=lambda: "DaVinci Resolve Studio",
        GetProjectManager=lambda: manager,
    )


def _wire_external(monkeypatch, tmp_path, app):
    """Install a fake scripting dir whose ``scriptapp`` returns ``app``."""
    modules = tmp_path / "Modules"
    modules.mkdir()
    (modules / "DaVinciResolveScript.py").write_text("", encoding="utf-8")
    monkeypatch.setenv(SCRIPT_API_ENV, str(tmp_path))

    class _Module:
        @staticmethod
        def scriptapp(name):
            return app

    monkeypatch.setitem(sys.modules, "DaVinciResolveScript", _Module)
    monkeypatch.setenv(ENV_VAR, EXTERNAL)


def _wire_in_process(monkeypatch, app):
    monkeypatch.setattr("builtins.resolve", app, raising=False)
    monkeypatch.setenv(ENV_VAR, IN_PROCESS)


@pytest.fixture(params=sorted(SCRIPTS))
def script_name(request):
    return request.param


@pytest.fixture(params=[EXTERNAL, IN_PROCESS])
def transport(request):
    return request.param


@pytest.fixture
def wired(transport, monkeypatch, tmp_path):
    if transport == EXTERNAL:
        _wire_external(monkeypatch, tmp_path, _app())
    else:
        _wire_in_process(monkeypatch, _app())
    return transport


def _run(name, monkeypatch, capsys, *args):
    path = SKILLS_DIR / SCRIPTS[name] / "scripts" / (name + ".py")
    monkeypatch.setattr(sys, "argv", [str(path)] + list(args))
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(path), run_name="__main__")
    captured = capsys.readouterr()
    assert captured.err == ""
    return excinfo.value.code, json.loads(captured.out)


def _call(script_name, monkeypatch, capsys, **kwargs):
    path = SKILLS_DIR / SCRIPTS[script_name] / "scripts" / (script_name + ".py")
    namespace = runpy.run_path(str(path))
    result = namespace["main"](**kwargs)
    assert capsys.readouterr() == ("", "")
    return result


class TestHostAbsent:
    """Resolve not running is a result, not a failure."""

    def test_scripts_report_absent_host(self, script_name, capsys, monkeypatch, tmp_path):
        _wire_external(monkeypatch, tmp_path, None)
        result = _call(script_name, monkeypatch, capsys)
        assert result["success"] is True
        assert result["context"]["host_available"] is False
        assert "start Resolve" in result["context"]["note"]

    def test_scripts_offer_no_transport_error_when_host_is_absent(self, script_name, capsys, monkeypatch, tmp_path):
        _wire_external(monkeypatch, tmp_path, None)
        result = _call(script_name, monkeypatch, capsys)
        assert not result["context"].get("transport_error")


class TestHostPresent:
    def test_all_scripts_succeed(self, wired, script_name, monkeypatch, capsys):
        result = _call(script_name, monkeypatch, capsys)
        assert result["success"] is True, result.get("message")
        assert result["context"]["host_available"] is True
        assert result["context"]["transport"] == wired

    def test_cli_exit_code_is_zero(self, wired, script_name, monkeypatch, capsys):
        code, payload = _run(script_name, monkeypatch, capsys)
        assert code == 0
        assert payload["host_available"] is True

    def test_mcp_entry_prints_nothing(self, wired, script_name, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["resolve", "--unrelated-host-argument"])
        assert _call(script_name, monkeypatch, capsys)["success"] is True


def test_session_info_reports_edition(wired, monkeypatch, capsys):
    result = _call("session_info", monkeypatch, capsys)
    assert result["context"]["host_edition"] == "studio"
    assert result["context"]["external_scripting_allowed"] is True


def test_list_projects_marks_the_current_project(wired, monkeypatch, capsys):
    result = _call("list_projects", monkeypatch, capsys)
    assert result["context"]["project_count"] == 2
    assert result["context"]["current_project"] == "Demo Project"
    assert [p["current"] for p in result["context"]["projects"]] == [True, False]


def test_project_info_reads_settings(wired, monkeypatch, capsys):
    result = _call("project_info", monkeypatch, capsys)
    project = result["context"]["project"]
    assert project["name"] == "Demo Project"
    assert project["timeline_count"] == 1
    assert project["settings"]["timelineFrameRate"] == "24"
    assert "unknownSetting" not in project["settings"]


def test_list_media_pool_walks_the_tree(wired, monkeypatch, capsys):
    result = _call("list_media_pool", monkeypatch, capsys)
    assert result["context"]["folder_count"] == 1
    assert result["context"]["folders"][0]["name"] == "Master"


@pytest.mark.parametrize("depth", [None, 1, 2])
def test_list_media_pool_honours_max_depth(wired, depth, monkeypatch, capsys):
    result = _call("list_media_pool", monkeypatch, capsys, max_depth=depth)
    assert result["success"] is True
    assert result["context"]["folder_count"] >= 1


@pytest.mark.parametrize("depth", [0, -1, True, "1", 1.5])
def test_list_media_pool_rejects_invalid_max_depth(wired, depth, monkeypatch, capsys):
    result = _call("list_media_pool", monkeypatch, capsys, max_depth=depth)
    assert result["success"] is False
    assert "positive integer" in result["message"]


def test_list_folder_clips_finds_a_named_folder(wired, monkeypatch, capsys):
    result = _call("list_folder_clips", monkeypatch, capsys, folder="Master")
    assert result["context"]["found"] is True
    assert result["context"]["folder"] == "Master"


def test_list_folder_clips_reports_a_missing_folder(wired, monkeypatch, capsys):
    result = _call("list_folder_clips", monkeypatch, capsys, folder="Nope")
    assert result["success"] is True
    assert result["context"]["found"] is False
    assert result["context"]["clips"] == []


def test_list_timelines_reports_track_counts(wired, monkeypatch, capsys):
    result = _call("list_timelines", monkeypatch, capsys)
    timelines = result["context"]["timelines"]
    assert timelines[0]["track_counts"] == {"video": 2, "audio": 3, "subtitle": 0}


def test_timeline_info_selects_by_name(wired, monkeypatch, capsys):
    result = _call("timeline_info", monkeypatch, capsys, name="Timeline 1")
    assert result["context"]["timeline"]["name"] == "Timeline 1"


def test_timeline_info_reports_an_unknown_name(wired, monkeypatch, capsys):
    result = _call("timeline_info", monkeypatch, capsys, name="Missing")
    assert result["context"]["timeline"] is None
    assert result["error"] == "not_found"


def test_timeline_info_reports_an_out_of_range_index(wired, monkeypatch, capsys):
    result = _call("timeline_info", monkeypatch, capsys, index=9)
    assert result["error"] == "out_of_range"


@pytest.mark.parametrize("index", [-1, True, "0"])
def test_timeline_info_rejects_an_invalid_index(wired, index, monkeypatch, capsys):
    result = _call("timeline_info", monkeypatch, capsys, index=index)
    assert result["error"] == "invalid_index"


def test_list_timeline_items_reads_track_one(wired, monkeypatch, capsys):
    result = _call("list_timeline_items", monkeypatch, capsys, track_type="video", track_index=1)
    assert result["context"]["item_count"] == 1
    assert result["context"]["items"][0]["name"] == "Shot 010"


def test_list_timeline_items_reports_a_track_that_does_not_exist(wired, monkeypatch, capsys):
    """Asking for a subtitle track on a timeline with none is out of range."""
    result = _call("list_timeline_items", monkeypatch, capsys, track_type="subtitle", track_index=1)
    assert result["success"] is False
    assert result["error"] == "out_of_range"
    assert result["context"]["items"] == []


def test_list_timeline_items_rejects_an_unknown_track_type(wired, monkeypatch, capsys):
    result = _call("list_timeline_items", monkeypatch, capsys, track_type="smell")
    assert result["error"] == "invalid_track_type"


@pytest.mark.parametrize("index", [0, -1, True])
def test_list_timeline_items_rejects_an_invalid_track_index(wired, index, monkeypatch, capsys):
    result = _call("list_timeline_items", monkeypatch, capsys, track_index=index)
    assert result["error"] == "invalid_track_index"


def test_list_gallery_albums_reports_still_counts(wired, monkeypatch, capsys):
    result = _call("list_gallery_albums", monkeypatch, capsys)
    assert result["context"]["albums"][0] == {"name": "Album 1", "still_count": 1}


def test_list_gallery_stills_reads_an_album(wired, monkeypatch, capsys):
    result = _call("list_gallery_stills", monkeypatch, capsys, album="Album 1")
    assert result["context"]["stills"][0]["label"] == "Teal & Orange"


def test_list_gallery_stills_reports_a_missing_album(wired, monkeypatch, capsys):
    result = _call("list_gallery_stills", monkeypatch, capsys, album="Nope")
    assert result["context"]["found"] is False


class TestFreeEditionGate:
    """The free edition cannot be reached externally; say so, do not guess."""

    @pytest.fixture(autouse=True)
    def _free_host(self, monkeypatch):
        free_app = _app()
        # Legacy free host: retain the pre-21.1 Python path.
        monkeypatch.setattr(free_app, "GetVersionString", lambda: "21.0.4")
        monkeypatch.setattr(free_app, "GetProductName", lambda: "DaVinci Resolve", raising=False)
        _wire_in_process(monkeypatch, free_app)

    def test_in_process_still_serves_every_tool(self, script_name, monkeypatch, capsys):
        """The free edition is not a broken install; in-process it works fully."""
        result = _call(script_name, monkeypatch, capsys)
        assert result["success"] is True, result.get("message")

    def test_session_info_reports_the_free_edition(self, monkeypatch, capsys):
        result = _call("session_info", monkeypatch, capsys)
        assert result["context"]["host_edition"] == "free"
        assert result["context"]["external_scripting_allowed"] is False


class TestFree21PythonGate:
    @pytest.fixture(autouse=True)
    def _free_host(self, monkeypatch):
        app = _app()
        monkeypatch.setattr(app, "GetProductName", lambda: "DaVinci Resolve", raising=False)
        monkeypatch.setattr(app, "GetVersionString", lambda: "21.1.1")
        _wire_in_process(monkeypatch, app)

    @pytest.mark.parametrize("script_name", [name for name in SCRIPTS if name != "session_info"])
    def test_host_operations_fail_with_python_requirement(self, script_name, monkeypatch, capsys):
        result = _call(script_name, monkeypatch, capsys)
        assert result["success"] is False
        assert "Python scripting requires" in result["message"]

    def test_session_reports_unsupported_python(self, monkeypatch, capsys):
        result = _call("session_info", monkeypatch, capsys)
        assert result["context"]["python_scripting_allowed"] is False
        assert result["context"]["transport_supported"] is False


@pytest.mark.parametrize("product,version", [("", "21.1"), ("DaVinci Resolve Studio", "unknown")])
def test_host_operations_do_not_assume_unknown_identity_is_supported(product, version, monkeypatch, capsys):
    app = _app()
    monkeypatch.setattr(app, "GetProductName", lambda: product, raising=False)
    monkeypatch.setattr(app, "GetVersionString", lambda: version)
    _wire_in_process(monkeypatch, app)
    result = _call("list_projects", monkeypatch, capsys)
    assert result["success"] is False
    assert "support is not established" in result["message"]
