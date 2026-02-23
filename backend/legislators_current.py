"""
Phone and contact_form URL from unitedstates/congress-legislators (legislators-current.json).
Used as fallback when Congress.gov API does not provide phone or contactFormUrl.
"""
from typing import Any, Optional

import httpx

try:
    from contact_validation import is_valid_contact_form_url
except ImportError:
    is_valid_contact_form_url = None

_LEGISLATORS_JSON = "https://unitedstates.github.io/congress-legislators/legislators-current.json"
# bioguide -> { "phone": str|None, "contact_form": str|None }
_index: Optional[dict[str, dict[str, Optional[str]]]] = None


def _load_index() -> dict[str, dict[str, Optional[str]]]:
    global _index
    if _index is not None:
        return _index
    result: dict[str, dict[str, Optional[str]]] = {}
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(_LEGISLATORS_JSON)
            if resp.status_code != 200:
                _index = result
                return result
            data = resp.json()
    except Exception:
        _index = result
        return result
    if not isinstance(data, list):
        _index = result
        return result
    for leg in data:
        if not isinstance(leg, dict):
            continue
        bid = None
        id_block = leg.get("id")
        if isinstance(id_block, dict):
            bid = id_block.get("bioguide")
        if not bid or not isinstance(bid, str):
            continue
        terms = leg.get("terms")
        if not isinstance(terms, list) or not terms:
            result[bid] = {"phone": None, "contact_form": None, "url": None}
            continue
        # Current term is the last one
        current = terms[-1] if isinstance(terms[-1], dict) else {}
        phone = current.get("phone")
        if isinstance(phone, str) and phone.strip():
            phone = phone.strip()
        else:
            phone = None
        cf = current.get("contact_form")
        if isinstance(cf, str) and cf.strip().startswith(("http://", "https://")):
            cf = cf.strip()
            if is_valid_contact_form_url is not None and not is_valid_contact_form_url(cf):
                cf = None
        else:
            cf = None
        url_term = current.get("url")
        if isinstance(url_term, str) and url_term.strip().startswith(("http://", "https://")):
            url_term = url_term.strip()
        else:
            url_term = None
        result[bid] = {"phone": phone, "contact_form": cf, "url": url_term}
    _index = result
    return result


def get_legislator_fallback(bioguide_id: str) -> dict[str, Optional[str]]:
    """
    Return phone, contact_form, and url for the given bioguide from legislators-current.
    Returns {"phone": None, "contact_form": None, "url": None} if not found or on error.
    """
    if not bioguide_id or not isinstance(bioguide_id, str):
        return {"phone": None, "contact_form": None, "url": None}
    bid = bioguide_id.strip()
    if not bid:
        return {"phone": None, "contact_form": None, "url": None}
    index = _load_index()
    return index.get(bid, {"phone": None, "contact_form": None, "url": None})
