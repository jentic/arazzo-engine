"""Utility functions for the Arazzo generator."""

import re


def to_kebab_case(s: str) -> str:
    """Convert a string to kebab-case format.

    Args:
        s: The string to convert

    Returns:
        The kebab-cased string
    """
    # Insert hyphens between camelCase transitions (e.g., camelCase -> camel-Case)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", s)

    # Replace spaces and underscores with hyphens
    s = re.sub(r"[\s_]+", "-", s)

    # Remove any characters that aren't alphanumeric or hyphens
    s = re.sub(r"[^a-zA-Z0-9\-]", "", s)

    # Convert to lowercase
    s = s.lower()

    # Remove leading/trailing hyphens
    s = s.strip("-")

    return s


def encode_json_pointer(path: str) -> str:
    """Encode a path segment for use in a JSON pointer.

    According to RFC 6901, '~' needs to be encoded as '~0' and '/' as '~1'.

    Args:
        path: The path segment to encode.

    Returns:
        The encoded path segment.
    """
    if not path:
        return ""

    # Replace ~ with ~0
    path = path.replace("~", "~0")
    # Replace / with ~1
    path = path.replace("/", "~1")

    return path
