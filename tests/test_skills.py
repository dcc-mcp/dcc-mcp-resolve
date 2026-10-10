"""Bundled skills stay structurally valid without a DaVinci Resolve host.

Static declarations and core's real discovery/registration path are checked
without importing host modules or contacting Resolve.
"""

from pathlib import Path

import pytest
import yaml
from dcc_mcp_core import SkillCatalog, ToolRegistry, validate_skill

SKILLS_DIR = Path(__file__).resolve().parents[1] / "src" / "dcc_mcp_resolve" / "skills"


def _skills():
    return sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir())


def test_at_least_one_skill_ships():
    assert _skills()


@pytest.mark.parametrize("skill_dir", _skills(), ids=lambda p: p.name)
def test_skill_has_a_readme(skill_dir):
    assert (skill_dir / "SKILL.md").is_file()


@pytest.mark.parametrize("skill_dir", _skills(), ids=lambda p: p.name)
def test_skill_front_matter_declares_name_and_dcc(skill_dir):
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n")
    front_matter = yaml.safe_load(text.split("---")[1])
    assert front_matter["name"] == skill_dir.name
    assert front_matter["metadata"]["dcc-mcp"]["dcc"] == "resolve"
    assert front_matter["metadata"]["dcc-mcp"]["tools"] == "tools.yaml"


@pytest.mark.parametrize("skill_dir", _skills(), ids=lambda p: p.name)
def test_every_declared_tool_script_exists(skill_dir):
    tools = yaml.safe_load((skill_dir / "tools.yaml").read_text(encoding="utf-8"))
    for tool in tools["tools"]:
        assert "script" not in tool
        assert "parameters" not in tool
        script = skill_dir / tool["source_file"]
        assert script.is_file(), "%s declares a missing script" % tool["name"]
        assert tool["input_schema"]["type"] == "object"
        assert isinstance(tool["input_schema"]["properties"], dict)
        assert tool["input_schema"]["additionalProperties"] is False
        assert tool["output_schema"]["type"] == "object"
        assert tool["read_only"] is True


@pytest.mark.parametrize("skill_dir", _skills(), ids=lambda p: p.name)
def test_tool_names_are_valid_identifiers(skill_dir):
    tools = yaml.safe_load((skill_dir / "tools.yaml").read_text(encoding="utf-8"))["tools"]
    for tool in tools:
        assert tool["name"].isidentifier()


@pytest.mark.parametrize("skill_dir", _skills(), ids=lambda p: p.name)
def test_every_tool_is_declared_read_only(skill_dir):
    """This adapter ships inspection only; no tool may mutate the project."""
    tools = yaml.safe_load((skill_dir / "tools.yaml").read_text(encoding="utf-8"))["tools"]
    for tool in tools:
        assert tool["read_only"] is True


@pytest.mark.parametrize("skill_dir", _skills(), ids=lambda p: p.name)
def test_skill_scripts_are_py37_parseable(skill_dir):
    import ast

    for script in (skill_dir / "scripts").glob("*.py"):
        source = script.read_text(encoding="utf-8")
        ast.parse(source, filename=str(script))


@pytest.mark.parametrize("skill_dir", _skills(), ids=lambda p: p.name)
def test_core_validates_bundled_skill(skill_dir):
    report = validate_skill(str(skill_dir))
    assert not [issue.message for issue in report.issues if issue.severity == "error"]


@pytest.mark.parametrize("skill_dir", _skills(), ids=lambda p: p.name)
def test_core_registers_declared_schema_and_source(skill_dir):
    registry = ToolRegistry()
    catalog = SkillCatalog(registry)
    catalog.discover([str(SKILLS_DIR)], "resolve")
    loaded = catalog.load_skill(skill_dir.name)
    declarations = yaml.safe_load((skill_dir / "tools.yaml").read_text(encoding="utf-8"))["tools"]
    assert set(loaded) == {skill_dir.name.replace("-", "_") + "__" + tool["name"] for tool in declarations}
    for tool in declarations:
        action = registry.get_action(skill_dir.name.replace("-", "_") + "__" + tool["name"])
        assert action["input_schema"] == tool["input_schema"]
        assert action["output_schema"] == tool["output_schema"]
        assert Path(action["source_file"]) == skill_dir / tool["source_file"]
        assert action["description"] == tool["description"]


def test_no_tool_exposes_a_generic_script_escape_hatch():
    """Resolve 21.1 already ships a run_script MCP server; do not clone it.

    Every tool must be a typed, validated operation rather than a passthrough
    that executes arbitrary host script.
    """
    names = []
    for skill_dir in _skills():
        tools = yaml.safe_load((skill_dir / "tools.yaml").read_text(encoding="utf-8"))["tools"]
        names.extend(tool["name"] for tool in tools)
    forbidden = {"run_script", "exec_script", "eval_script", "execute", "run_lua", "run_python"}
    assert not forbidden.intersection(names)


def test_list_media_pool_declares_positive_integer_max_depth():
    tools = yaml.safe_load((SKILLS_DIR / "resolve-media-pool" / "tools.yaml").read_text(encoding="utf-8"))["tools"]
    limit = next(tool for tool in tools if tool["name"] == "list_media_pool")["input_schema"]["properties"]["max_depth"]
    assert limit["type"] == "integer"
    assert limit["minimum"] == 1


def test_list_timeline_items_constrains_track_type():
    tools = yaml.safe_load((SKILLS_DIR / "resolve-timeline" / "tools.yaml").read_text(encoding="utf-8"))["tools"]
    tool = next(tool for tool in tools if tool["name"] == "list_timeline_items")
    track = tool["input_schema"]["properties"]["track_type"]
    assert set(track["enum"]) == {"video", "audio", "subtitle"}
    assert tool["input_schema"]["properties"]["track_index"]["minimum"] == 1
