"""Resolve version parsing, edition classification, and the Studio gate."""

from dcc_mcp_resolve.compat import (
    FREE,
    STUDIO,
    SUPPORTED_MAJOR_LINES,
    external_scripting_allowed,
    is_supported,
    major_line,
    parse_edition,
    parse_version_string,
)


def test_parse_version_string_splits_major_minor():
    assert parse_version_string("21.1.0.18") == (21.1, "21.1.0.18")


def test_parse_version_string_without_enough_components():
    assert parse_version_string("21") == (None, "21")


def test_parse_version_string_handles_empty():
    assert parse_version_string("") == (None, "")
    assert parse_version_string(None) == (None, "")


def test_major_line():
    assert major_line("21.1.0.18") == "21"
    assert major_line("18.6") == "18"


def test_supported_lines_cover_18_to_21():
    assert SUPPORTED_MAJOR_LINES == ("18", "19", "20", "21")


def test_current_release_is_supported():
    assert is_supported("21.1.0.18") is True


def test_unsupported_major_line():
    assert is_supported("17.4") is False


def test_unknown_version_is_not_supported():
    assert is_supported("") is False


def test_studio_edition_is_detected():
    assert parse_edition("DaVinci Resolve Studio") == STUDIO


def test_free_edition_is_detected():
    assert parse_edition("DaVinci Resolve") == FREE


def test_edition_detection_is_case_insensitive():
    assert parse_edition("davinci resolve studio") == STUDIO


def test_missing_product_name_is_treated_as_free():
    assert parse_edition("") == FREE
    assert parse_edition(None) == FREE


def test_studio_allows_external_scripting():
    assert external_scripting_allowed("21.1", "DaVinci Resolve Studio") is True


def test_free_edition_blocks_external_scripting_from_19_1():
    """The Studio gate is the constraint that shapes the whole adapter."""
    assert external_scripting_allowed("21.1", "DaVinci Resolve") is False
    assert external_scripting_allowed("19.1", "DaVinci Resolve") is False


def test_free_edition_allowed_external_scripting_before_19_1():
    assert external_scripting_allowed("18.6", "DaVinci Resolve") is True


def test_unparseable_version_is_unknown_not_false():
    """'Cannot tell' must not be reported as 'definitely blocked'."""
    assert external_scripting_allowed("", "DaVinci Resolve") is None
    assert external_scripting_allowed("not-a-version", "DaVinci Resolve Studio") is None
