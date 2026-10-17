"""Resolve version parsing, edition classification, and the Studio gate."""

import pytest

from dcc_mcp_resolve.compat import (
    FREE,
    STUDIO,
    SUPPORTED_MAJOR_LINES,
    external_scripting_allowed,
    is_supported,
    major_line,
    parse_edition,
    parse_version_string,
    python_scripting_allowed,
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


def test_missing_product_name_is_unknown():
    assert parse_edition("") is None
    assert parse_edition(None) is None


def test_studio_allows_external_scripting():
    assert external_scripting_allowed("21.1", "DaVinci Resolve Studio") is True


def test_free_edition_blocks_external_scripting_from_19_1():
    """The Studio gate is the constraint that shapes the whole adapter."""
    assert external_scripting_allowed("21.1", "DaVinci Resolve") is False
    assert external_scripting_allowed("19.1", "DaVinci Resolve") is False


def test_free_edition_already_blocks_external_scripting_in_18_6():
    assert external_scripting_allowed("18.6", "DaVinci Resolve") is False


def test_unparseable_version_is_unknown_not_false():
    """'Cannot tell' must not be reported as 'definitely blocked'."""
    assert external_scripting_allowed("", "DaVinci Resolve") is None
    assert external_scripting_allowed("not-a-version", "DaVinci Resolve Studio") is None


@pytest.mark.parametrize("version", ["18.6", "19.0", "19.1", "20.3.3", "21.0.4"])
def test_legacy_free_python_path_is_preserved(version):
    assert python_scripting_allowed(version, "DaVinci Resolve") is True


@pytest.mark.parametrize("version", ["21.1", "21.1.1.10", "21.10"])
def test_new_free_python_path_is_blocked(version):
    assert python_scripting_allowed(version, "DaVinci Resolve") is False
    assert python_scripting_allowed(version, "DaVinci Resolve Studio") is True


@pytest.mark.parametrize("check", [python_scripting_allowed, external_scripting_allowed])
@pytest.mark.parametrize(
    "version,product",
    [
        (None, "DaVinci Resolve Studio"),
        ("21", "DaVinci Resolve Studio"),
        ("21.bad", "DaVinci Resolve Studio"),
        ("22.0", "DaVinci Resolve Studio"),
        ("21.1", None),
        ("21.1", ""),
        ("21.1", "unknown product"),
    ],
)
def test_unknown_identity_does_not_claim_support(check, version, product):
    assert check(version, product) is None


@pytest.mark.parametrize("version", ["21", "21.bad", "22.0"])
def test_malformed_or_unsupported_version_is_not_supported(version):
    assert is_supported(version) is False
