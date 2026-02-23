"""
Congress.gov API v3 client: members by state/district, member detail, bills, votes.
Uses CONGRESS_API_KEY from config. Caches responses in memory with TTL (long for member bio, short for votes/bills).
"""
import time
from typing import Any, Optional

import httpx

from config import CONGRESS_API_KEY, CONGRESS_BASE_URL, CURRENT_CONGRESS, CONGRESS_FOR_MEMBER_LOOKUP

try:
    from contact_validation import (
        is_valid_contact_form_url as _is_valid_contact_form_url,
        is_valid_member_website_url as _is_valid_member_website_url,
    )
except ImportError:
    _is_valid_contact_form_url = None
    _is_valid_member_website_url = None
try:
    from contact_congress import get_contact_form_url as _contact_congress_url
except ImportError:
    _contact_congress_url = None
try:
    from legislators_current import get_legislator_fallback as _legislator_fallback
except ImportError:
    _legislator_fallback = None

# In-memory cache: key -> (expires_at, data). Long TTL for member info (7 days), short for votes/bills (1 hour).
_CACHE: dict[str, tuple[float, Any]] = {}
_MEMBER_TTL = 7 * 24 * 3600   # 7 days
_VOTES_BILLS_TTL = 3600       # 1 hour


def _cache_get(key: str) -> Optional[Any]:
    if key not in _CACHE:
        return None
    expires, data = _CACHE[key]
    if time.time() > expires:
        del _CACHE[key]
        return None
    return data


def _cache_set(key: str, data: Any, ttl: float):
    _CACHE[key] = (time.time() + ttl, data)


def _url(path: str, **params: Any) -> str:
    base = CONGRESS_BASE_URL.rstrip("/")
    path = path if path.startswith("/") else "/" + path
    params.setdefault("api_key", CONGRESS_API_KEY)
    q = "&".join(f"{k}={v}" for k, v in params.items() if v is not None and v != "")
    return f"{base}{path}?format=json&{q}" if q else f"{base}{path}?format=json"


def _get(path: str, cache_key: Optional[str] = None, ttl: float = _MEMBER_TTL, **params: Any) -> dict:
    # Don't pass cache_key/ttl to URL
    url_params = {k: v for k, v in params.items() if k not in ("cache_key", "ttl")}
    if cache_key and CONGRESS_API_KEY:
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached
    url = _url(path, **url_params)
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()
    if cache_key and CONGRESS_API_KEY:
        _cache_set(cache_key, data, ttl)
    return data


def _extract_members_list(data: dict) -> list:
    """Congress API may return members in 'members', 'results', or wrap in pagination."""
    if not data:
        return []
    members = data.get("members") or data.get("results") or data.get("data")
    if isinstance(members, list):
        return members
    if isinstance(data.get("member"), dict):
        return [data["member"]]
    return []


def get_member_house(state: str, district: int) -> Optional[dict]:
    """Get House member for state + district. API: /member/congress/{congress}/{state}/{district}?currentMember=true"""
    state = state.upper()[:2]
    for congress in (CURRENT_CONGRESS, CONGRESS_FOR_MEMBER_LOOKUP):
        try:
            data = _get(
                f"/member/congress/{congress}/{state}/{district}",
                currentMember="true",
                cache_key=f"house:{state}:{district}:{congress}",
            )
            members = _extract_members_list(data)
            if members:
                return _normalize_member(members[0])
            # Single member response
            if isinstance(data, dict) and data.get("bioguideId"):
                return _normalize_member(data)
        except Exception:
            continue
    return None


def _get_member_list_congress() -> list[dict]:
    """Fetch all current members (cached). Try CURRENT_CONGRESS (119) first, then fall back to 118."""
    all_members = []
    for congress in (CURRENT_CONGRESS, CONGRESS_FOR_MEMBER_LOOKUP):
        offset = 0
        limit = 250
        while True:
            cache_key = f"member_list:{congress}:{offset}" if offset == 0 else None
            try:
                data = _get(
                    f"/member/congress/{congress}",
                    currentMember="true",
                    limit=limit,
                    offset=offset,
                    cache_key=cache_key,
                )
            except Exception:
                break
            members = _extract_members_list(data)
            if not members:
                break
            all_members.extend(members)
            if len(members) < limit:
                return all_members
            offset += len(members)
    return all_members


# State name -> two-letter code for senator filter (member list has "state": "Illinois" etc.)
_STATE_TO_ABBREV = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD", "massachusetts": "MA",
    "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO", "montana": "MT",
    "nebraska": "NE", "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
}


def _member_state_abbrev(m: dict) -> str:
    """Two-letter state from member or term; API may give 'Illinois' or 'IL'."""
    raw = (m.get("state") or "").strip()
    if len(raw) == 2:
        return raw.upper()
    return _STATE_TO_ABBREV.get(raw.lower(), raw.upper()[:2] if raw else "")


def get_members_senate(state: str) -> list[dict]:
    """Get both Senators for state."""
    state = state.upper()[:2]
    try:
        members = _get_member_list_congress()
        out = []
        for m in members:
            terms = _terms_list(m)
            for t in terms:
                if "Senate" not in str(t.get("chamber", "")):
                    continue
                # State may be on term or on member (list endpoint often has member.state only)
                term_state = (t.get("state") or "").strip().upper()
                if len(term_state) == 2:
                    st_abbrev = term_state
                else:
                    st_abbrev = _member_state_abbrev(m)
                if st_abbrev == state:
                    out.append(_normalize_member(m))
                    if len(out) == 2:
                        return out
                    break
        return out
    except Exception:
        pass
    return []


def get_members_for_district(state: str, district: int) -> dict:
    """Return House member + 2 Senators for state/district. Keys: representative, senators, districtInfo."""
    rep = get_member_house(state, district)
    senators = get_members_senate(state)
    state_names = {
        "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
        "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
        "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
        "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts",
        "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
        "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
        "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
        "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
        "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
        "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
    }
    state_name = state_names.get(state.upper(), state)
    district_label = f"{state.upper()}-{district}" if district else state.upper()
    ord_suffix = "th" if 10 <= district % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(district % 10, "th")
    district_ord = f"{district}{ord_suffix}" if district else "at-large"
    label = f"{state_name}'s {district_ord} Congressional District" if district else f"{state_name} (at-large)"
    return {
        "districtInfo": {
            "state": state.upper(),
            "district": district,
            "districtLabel": district_label,
            "stateName": state_name,
            "label": label,
        },
        "representative": rep,
        "senators": senators[:2],
    }


def _terms_list(m: dict) -> list:
    """Congress API v3 may return terms as a list or as { 'item': [ ... ] }."""
    raw = m.get("terms")
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and "item" in raw:
        i = raw["item"]
        return i if isinstance(i, list) else []
    return []


def _normalize_party(raw: Any) -> Optional[str]:
    """Return consistent party string: Republican, Democratic, or original if other (e.g. Independent)."""
    if not raw:
        return None
    s = (str(raw) or "").strip()
    if not s:
        return None
    lower = s.lower()
    if lower in ("republican", "r"):
        return "Republican"
    if lower in ("democratic", "d"):
        return "Democratic"
    return s


def _normalize_member(m: dict) -> dict:
    """Extract a flat member object for API response. Handles Congress API v3 camelCase."""
    if not m or not isinstance(m, dict):
        return m
    terms = _terms_list(m)
    current = terms[-1] if terms else {}
    # Chamber can be "House of Representatives" or "House"
    chamber = (current.get("chamber") or m.get("chamber") or "").lower()
    if "house" in chamber and "senate" not in chamber:
        chamber = "house"
    name = (
        m.get("name")
        or (str(current.get("firstName") or "").strip() + " " + str(current.get("lastName") or "").strip()).strip()
        or (str(m.get("firstName") or "").strip() + " " + str(m.get("lastName") or "").strip()).strip()
    )
    uid = m.get("bioguideId") or m.get("id")
    if uid is None and terms:
        uid = current.get("bioguideId") or current.get("id")
    raw_party = current.get("party") or m.get("party") or current.get("partyName") or m.get("partyName")
    party = _normalize_party(raw_party) or raw_party
    contact_form_url = _member_contact_form_url(m)
    email = _member_email(m)
    bioguide = m.get("bioguideId") or (str(uid) if uid is not None else None)
    phone = _member_phone(m)
    member_url = m.get("url") or current.get("url")
    if isinstance(member_url, str):
        member_url = member_url.strip() or None
    if _legislator_fallback and bioguide:
        fallback = _legislator_fallback(bioguide)
        if not phone and fallback.get("phone"):
            phone = fallback["phone"]
        if not email and not contact_form_url and fallback.get("contact_form"):
            contact_form_url = fallback["contact_form"]
        if _is_valid_member_website_url and not _is_valid_member_website_url(member_url) and fallback.get("url"):
            member_url = fallback["url"]
        elif not member_url and fallback.get("url"):
            member_url = fallback["url"]
    if not email and not contact_form_url and bioguide and _contact_congress_url:
        candidate = _contact_congress_url(bioguide)
        if candidate and (_is_valid_contact_form_url is None or _is_valid_contact_form_url(candidate)):
            contact_form_url = candidate
    return {
        "id": str(uid) if uid is not None else None,
        "bioguideId": m.get("bioguideId"),
        "name": name or "Unknown",
        "firstName": m.get("firstName") or current.get("firstName"),
        "lastName": m.get("lastName") or current.get("lastName"),
        "party": party,
        "state": current.get("state") or m.get("state"),
        "district": current.get("district"),
        "chamber": chamber,
        "phone": phone,
        "url": member_url,
        "nextElection": current.get("endYear"),
        "firstElected": current.get("startYear") if terms else None,
        "email": email,
        "contactFormUrl": contact_form_url if not email else None,
    }


def _member_phone(m: dict) -> Optional[str]:
    # Congress API may have phone in different places
    terms = _terms_list(m)
    for t in reversed(terms):
        if t.get("phone"):
            return t.get("phone")
    return m.get("phone")


def _member_email(m: dict) -> Optional[str]:
    """Extract email from member or terms if Congress API provides it."""
    terms = _terms_list(m)
    for t in reversed(terms):
        email = t.get("email") or t.get("contactForm")
        if isinstance(email, str) and "@" in email:
            return email.strip() or None
    raw = m.get("email") or m.get("contactForm")
    if isinstance(raw, str) and "@" in raw:
        return raw.strip() or None
    return None


def _member_contact_form_url(m: dict) -> Optional[str]:
    """Extract contact form URL from member or terms if API provides it (when no direct email)."""
    terms = _terms_list(m)
    for t in reversed(terms):
        url = t.get("contactForm") or t.get("contactFormUrl")
        if isinstance(url, str) and url.strip().startswith("http"):
            u = url.strip()
            if _is_valid_contact_form_url is None or _is_valid_contact_form_url(u):
                return u
            return None
    raw = m.get("contactForm") or m.get("contactFormUrl")
    if isinstance(raw, str) and raw.strip().startswith("http"):
        u = raw.strip()
        if _is_valid_contact_form_url is None or _is_valid_contact_form_url(u):
            return u
    return None


def get_member(bioguide_id: str) -> Optional[dict]:
    """Get single member by bioguide ID. API returns { member: {...} }."""
    cache_key = f"member:{bioguide_id}"
    try:
        data = _get(f"/member/{bioguide_id}", cache_key=cache_key)
        if data:
            m = data.get("member") or data
            if isinstance(m, dict):
                return _normalize_member(m)
    except Exception:
        pass
    return None


def get_member_bills(bioguide_id: str, limit: int = 20) -> list[dict]:
    """Bills member sponsors (active). API: /member/{bioguideId}/sponsored-legislation."""
    cache_key = f"bills:{bioguide_id}"
    try:
        data = _get(f"/member/{bioguide_id}/sponsored-legislation", limit=limit, cache_key=cache_key, ttl=_VOTES_BILLS_TTL)
        items = data.get("sponsoredLegislation") or data.get("bills") or []
        if not isinstance(items, list):
            items = []
        return [_norm_bill(b) for b in items[:limit]]
    except Exception:
        pass
    return []


def get_member_votes(bioguide_id: str, limit: int = 20) -> list[dict]:
    """Recent votes for member. Note: Congress API may use house-vote or different path; return empty if not available."""
    cache_key = f"votes:{bioguide_id}"
    try:
        # Member votes might be under a different endpoint; try member votes if it exists
        data = _get(f"/member/{bioguide_id}/votes", limit=limit, cache_key=cache_key, ttl=_VOTES_BILLS_TTL)
        items = data.get("votes") or []
        if isinstance(items, list):
            return [_norm_vote(v) for v in items[:limit]]
    except Exception:
        pass
    return []


def _norm_bill(b: Any) -> dict:
    if not isinstance(b, dict):
        return {"title": str(b), "url": None, "status": None}
    latest_action = b.get("latestAction")
    if isinstance(latest_action, dict):
        status = latest_action.get("text") or latest_action.get("description") or latest_action.get("actionDate")
    elif isinstance(latest_action, str):
        status = latest_action
    else:
        status = latest_action
    if not status:
        status = b.get("status") or b.get("currentStatus")
    # Congress API may return currentStatus/status as an object with name/description
    if isinstance(status, dict):
        status = status.get("name") or status.get("description") or status.get("text")
    return {
        "number": b.get("number"),
        "title": b.get("title") or b.get("shortTitle") or b.get("displayNumber"),
        "url": b.get("url") or b.get("congressUrl"),
        "introducedDate": b.get("introducedDate"),
        "status": str(status).strip() if status else None,
    }


def _norm_vote(v: Any) -> dict:
    if not isinstance(v, dict):
        return {"position": None, "description": str(v)}
    return {
        "position": v.get("position") or v.get("vote"),
        "description": v.get("description") or v.get("question"),
        "date": v.get("date"),
        "url": v.get("url"),
    }
