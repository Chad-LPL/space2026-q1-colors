"""
Shared validation for contact form URLs. Rejects non-congressional domains
so we never send users to e.g. google.com or example.com.
"""
from typing import Optional
from urllib.parse import urlparse


def is_valid_contact_form_url(url: Optional[str]) -> bool:
    """
    Return True only if the URL host is plausibly congressional
    (house.gov, senate.gov, congress.gov). Rejects google.com, example.com, etc.
    """
    if not url or not isinstance(url, str):
        return False
    s = url.strip()
    if not s.lower().startswith(("http://", "https://")):
        return False
    try:
        parsed = urlparse(s)
        host = (parsed.netloc or "").lower()
        if not host:
            return False
        # Allow only congressional domains
        if "house.gov" in host or "senate.gov" in host or "congress.gov" in host:
            return True
        return False
    except Exception:
        return False


def is_valid_member_website_url(url: Optional[str]) -> bool:
    """
    Return True if the URL looks like a member's official website
    (house.gov, senate.gov), not an API or JSON endpoint.
    """
    if not url or not isinstance(url, str):
        return False
    s = url.strip().lower()
    if not s.startswith(("http://", "https://")):
        return False
    # Reject API / JSON endpoints
    if "api.congress.gov" in s or "/api/" in s:
        return False
    if "house.gov" in s or "senate.gov" in s or "congress.gov" in s:
        return True
    return False
