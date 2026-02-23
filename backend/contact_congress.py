"""
Contact form URLs from unitedstates/contact-congress (GitHub).
Fetches member YAML by bioguide ID, extracts the first 'visit' URL from contact_form.steps.
Used when Congress.gov API does not provide email or contactFormUrl.
"""
from typing import Optional

import httpx
import yaml

from contact_validation import is_valid_contact_form_url

_CONTACT_CONGRESS_RAW = "https://raw.githubusercontent.com/unitedstates/contact-congress/master/members"
# In-memory cache: bioguide_id -> contact_form_url (no TTL; data changes rarely)
_url_cache: dict[str, str] = {}


def get_contact_form_url(bioguide_id: str) -> Optional[str]:
    """
    Return the contact form URL for the given bioguide ID from contact-congress data.
    Returns None if not found or on fetch/parse error. Results are cached in memory.
    """
    if not bioguide_id or not isinstance(bioguide_id, str):
        return None
    bid = bioguide_id.strip()
    if not bid:
        return None
    if bid in _url_cache:
        return _url_cache[bid] or None
    url = f"{_CONTACT_CONGRESS_RAW}/{bid}.yaml"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                _url_cache[bid] = ""
                return None
            data = yaml.safe_load(resp.text)
    except Exception:
        _url_cache[bid] = ""
        return None
    if not data or not isinstance(data, dict):
        _url_cache[bid] = ""
        return None
    contact_form = data.get("contact_form")
    if not contact_form or not isinstance(contact_form, dict):
        _url_cache[bid] = ""
        return None
    steps = contact_form.get("steps")
    if not steps or not isinstance(steps, list):
        _url_cache[bid] = ""
        return None
    for step in steps:
        if not isinstance(step, dict):
            continue
        visit = step.get("visit")
        if isinstance(visit, str) and visit.strip().lower().startswith(("http://", "https://")):
            out = visit.strip()
            if not is_valid_contact_form_url(out):
                _url_cache[bid] = ""
                return None
            _url_cache[bid] = out
            return out
    _url_cache[bid] = ""
    return None
