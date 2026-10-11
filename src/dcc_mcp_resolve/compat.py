"""DaVinci Resolve host compatibility matrix.

``Resolve.GetVersionString()`` returns a display string such as ``21.1.0.18``,
and ``Resolve.GetProductName()`` returns ``DaVinci Resolve Studio`` or
``DaVinci Resolve``. External scripting requires Studio. Since Resolve 21.1,
Python scripting also requires Studio, including the Python in-process transport.

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

# Blackmagic moved Python scripting to Studio in 21.1. Compare components,
# not floats: 21.10 is later than 21.1.
PYTHON_SCRIPTING_STUDIO_ONLY_FROM = (21, 1)


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
    return parse_version_string(raw)[0] is not None and major_line(raw) in SUPPORTED_MAJOR_LINES


def parse_edition(product_name):
    """Classify a ``GetProductName()`` value as :data:`STUDIO` or :data:`FREE`."""
    text = (product_name or "").strip().lower()
    if "davinci resolve" not in text:
        return None
    return STUDIO if STUDIO_MARKER in text else FREE


def external_scripting_allowed(version_string, product_name):
    """Declared external compatibility, or None for unknown/unsupported hosts.

    External scripting requires Studio on the supported release lines. The
    vendor already documented that requirement for 18.6; 19.1 is not its start.
    This is not proof that the host is reachable or configured correctly.
    """
    edition = parse_edition(product_name)
    if not is_supported(version_string) or edition is None:
        return None
    return edition == STUDIO


def python_scripting_allowed(version_string, product_name):
    """Declared Python compatibility, including in-process scripts.

    Resolve 21.1 release notes move Python scripting to Studio. Earlier free
    in-process behavior is retained as a declared path, not live validation.
    """
    edition = parse_edition(product_name)
    if not is_supported(version_string) or edition is None:
        return None
    version = tuple(int(part) for part in version_string.strip().split(".")[:2])
    return edition == STUDIO or version < PYTHON_SCRIPTING_STUDIO_ONLY_FROM
