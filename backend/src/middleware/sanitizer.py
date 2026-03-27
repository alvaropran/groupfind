"""Input sanitization utilities to prevent XSS."""

import html
import re

# Pattern to strip HTML tags
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def sanitize_text(text: str | None) -> str | None:
    """Sanitize user-facing text to prevent XSS.

    Strips HTML tags and escapes special characters.
    """
    if text is None:
        return None

    # Strip HTML tags
    cleaned = HTML_TAG_PATTERN.sub("", text)
    # Escape remaining HTML entities
    cleaned = html.escape(cleaned, quote=True)

    return cleaned


def sanitize_dict(data: dict, keys: list[str]) -> dict:
    """Sanitize specific string fields in a dictionary.

    Returns a new dictionary with sanitized values (immutable pattern).
    """
    result = dict(data)
    for key in keys:
        if key in result and isinstance(result[key], str):
            result[key] = sanitize_text(result[key])
    return result
