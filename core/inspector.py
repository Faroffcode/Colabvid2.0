"""Basic URL inspection helpers."""

from urllib.parse import urlparse


SUPPORTED_SCHEMES = {"http", "https"}


def inspect_url(url: str) -> dict[str, str | bool]:
    """Validate URL structure without downloading or making network requests."""
    cleaned = url.strip()
    parsed = urlparse(cleaned)
    valid = parsed.scheme in SUPPORTED_SCHEMES and bool(parsed.netloc)

    return {
        "url": cleaned,
        "scheme": parsed.scheme,
        "host": parsed.netloc,
        "valid": valid,
    }
