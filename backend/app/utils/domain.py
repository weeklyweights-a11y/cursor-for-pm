"""
Domain normalization for customer matching and enrichment.

Single source of truth: lowercase, strip www., strip protocol, strip trailing slash.
Used in customer upload, enrichment, and domain_mappings.
"""

import re


def normalize_domain(raw: str) -> str:
    """
    Normalize a domain or URL for consistent comparison and storage.

    Lowercase, strip http(s)://, strip www., strip trailing slash and path.
    Empty or whitespace input returns empty string.

    Args:
        raw: Raw domain, URL, or email domain (e.g. "https://www.Acme.com/", "acme.com").

    Returns:
        Normalized domain string, e.g. "acme.com".
    """
    if not raw or not isinstance(raw, str):
        return ""
    s = raw.strip().lower()
    if not s:
        return ""
    # Strip protocol
    s = re.sub(r"^https?://", "", s)
    # Strip www.
    if s.startswith("www."):
        s = s[4:]
    # Strip path and trailing slash (take only host part)
    if "/" in s:
        s = s.split("/", 1)[0]
    s = s.rstrip("/")
    return s
