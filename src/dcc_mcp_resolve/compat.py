"""DaVinci Resolve host compatibility matrix.

``Resolve.GetVersionString()`` returns a display string such as ``21.1.0.18``,
and ``Resolve.GetProductName()`` returns ``DaVinci Resolve Studio`` or
``DaVinci Resolve``. The edition decides the transport: external scripting has
been a Studio-only feature since roughly Resolve 19.1, so the free edition
cannot be reached from another process at all.

The current CI suite is host-free, so a version row here is a *declared*
support statement, not CI-verified evidence. See ``docs/validation/README.md``.
"""

SUPPORTED_MAJOR_LINES = ("18", "19", "20", "21")

MINIMUM_VERSION = "18.0"

TARGET_VERSION = "21.1"

STUDIO = "studio"

FREE = "free"

EDITIONS = (STUDIO, FREE)

# GetProductName() returns the full display name; the Studio marker is a
# substring rather than a suffix because the name also carries the platform
# on some builds.
STUDIO_MARKER = "studio"

# The minor release from which Blackmagic requires Studio for external
# scripting. Below this line the free edition accepted external connections.
EXTERNAL_SCRIPTING_STUDIO_ONLY_FROM = 19.1


def parse_version_string(raw):
    """Split a ``GetVersionString()`` value into ``(major_minor, full)``.

    Returns ``(None, text)`` when the string does not start with a numeric
    component, so callers can distinguish "unparseable" from "absent".
    """
    text = (raw or "").strip()
    if not text:
        return None, text
    parts = text.split(".")
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return None, text
    return float("%s.%s" % (parts[0], parts[1])), text


def major_line(raw):
    """Return the major release line of a ``GetVersionString()`` value."""
    text = (raw or "").strip()
    return text.split(".")[0] if text else ""


def is_supported(raw):
    """Whether a reported Resolve version falls on a supported major line."""
    return major_line(raw) in SUPPORTED_MAJOR_LINES


def parse_edition(product_name):
    """Classify a ``GetProductName()`` value as :data:`STUDIO` or :data:`FREE`."""
    text = (product_name or "").strip().lower()
    return STUDIO if STUDIO_MARKER in text else FREE


def external_scripting_allowed(version_string, product_name):
    """Whether this host accepts external scripting connections.

    Returns ``None`` when the version cannot be parsed, because the answer is
    then genuinely unknown rather than known-negative.
    """
    parsed, _ = parse_version_string(version_string)
    if parsed is None:
        return None
    if parsed < EXTERNAL_SCRIPTING_STUDIO_ONLY_FROM:
        return True
    return parse_edition(product_name) == STUDIO
