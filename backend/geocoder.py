"""
Census Geocoder: address -> lat/lng and congressional district (119th).
No API key required. Uses geographies endpoint to get district.
"""
from typing import Any, List, Optional

import httpx

from config import CENSUS_GEOCODER_URL

# 119th Congress - use current vintage for district lookup
BENCHMARK = "Public_AR_Current"
VINTAGE = "Current_Current"


def geocode_suggest(address: str, limit: int = 5) -> List[dict]:
    """
    Return up to `limit` address suggestions for typeahead.
    Each item: { "address": matchedAddress } from Census.
    """
    if not address or not address.strip() or len(address.strip()) < 3:
        return []
    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(
                CENSUS_GEOCODER_URL,
                params={
                    "address": address.strip(),
                    "benchmark": BENCHMARK,
                    "vintage": VINTAGE,
                    "layers": "118th Congressional Districts",
                    "format": "json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []
    matches = data.get("result", {}).get("addressMatches") or []
    out = []
    seen = set()
    for m in matches[:limit]:
        addr = (m.get("matchedAddress") or m.get("address", {}).get("address") or "").strip()
        if addr and addr not in seen:
            seen.add(addr)
            out.append({"address": addr})
    return out


def geocode(address: str) -> Optional[dict]:
    """
    Geocode one-line address and return state, district, lat, lng, districtLabel.
    Returns None if not found or error.
    """
    if not address or not address.strip():
        return None
    try:
        with httpx.Client(timeout=15.0) as client:
            # Census Geocoder: geographies/onelineaddress accepts one full address string
            resp = client.get(
                CENSUS_GEOCODER_URL,
                params={
                    "address": address.strip(),
                    "benchmark": BENCHMARK,
                    "vintage": VINTAGE,
                    "layers": "118th Congressional Districts",
                    "format": "json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return None

    matches = data.get("result", {}).get("addressMatches") or []
    if not matches:
        return None

    # Use first match
    m = matches[0]
    coords = m.get("coordinates", {})
    lat = coords.get("y")
    lng = coords.get("x")
    if lat is None or lng is None:
        return None

    # Geographies: 118th Congressional Districts (or 119th) - state + district number
    geos = m.get("geographies", {})
    # Key might be "118th Congressional Districts" or "Congressional Districts"
    cd_list = geos.get("118th Congressional Districts") or geos.get("119th Congressional Districts") or geos.get("Congressional Districts") or []
    state = None
    district = None
    if cd_list:
        first = cd_list[0] if isinstance(cd_list, list) else cd_list
        if isinstance(first, dict):
            # DISTRICT can be "01" or "00" for at-large
            state = first.get("STATE")
            dist = first.get("DISTRICT") or first.get("CD118") or first.get("CD119")
            if dist is not None:
                try:
                    district = int(dist) if str(dist).isdigit() else None
                except (ValueError, TypeError):
                    district = None

    # Fallback: try GEOID or NAME parsing (e.g. "06" for state, "15" for district)
    if (state is None or district is None) and cd_list:
        first = cd_list[0] if isinstance(cd_list, list) else cd_list
        if isinstance(first, dict) and first.get("GEOID"):
            geoid = str(first["GEOID"])
            if len(geoid) >= 4:
                state = geoid[:2]
                try:
                    district = int(geoid[2:])
                except ValueError:
                    district = 0

    if state is None:
        return None
    if district is None:
        district = 0

    state_names = {
        "01": "Alabama", "02": "Alaska", "04": "Arizona", "05": "Arkansas", "06": "California",
        "08": "Colorado", "09": "Connecticut", "10": "Delaware", "11": "Florida", "12": "Georgia",
        "15": "Hawaii", "16": "Idaho", "17": "Illinois", "18": "Indiana", "19": "Iowa", "20": "Kansas",
        "21": "Kentucky", "22": "Louisiana", "23": "Maine", "24": "Maryland", "25": "Massachusetts",
        "26": "Michigan", "27": "Minnesota", "28": "Mississippi", "29": "Missouri", "30": "Montana",
        "31": "Nebraska", "32": "Nevada", "33": "New Hampshire", "34": "New Jersey", "35": "New Mexico",
        "36": "New York", "37": "North Carolina", "38": "North Dakota", "39": "Ohio", "40": "Oklahoma",
        "41": "Oregon", "42": "Pennsylvania", "44": "Rhode Island", "45": "South Carolina", "46": "South Dakota",
        "47": "Tennessee", "48": "Texas", "49": "Utah", "50": "Vermont", "51": "Virginia", "53": "Washington",
        "54": "West Virginia", "55": "Wisconsin", "56": "Wyoming", "72": "Puerto Rico",
    }
    # State from Census is often FIPS; convert to 2-letter if needed
    state_abbrev = _fips_to_abbrev.get(str(state).zfill(2)) or state
    if len(str(state)) == 2 and str(state).isalpha():
        state_abbrev = str(state).upper()
    state_name = state_names.get(str(state).zfill(2), state_abbrev)
    district_label = f"{state_abbrev}-{district}" if district else state_abbrev
    ord_suffix = "th" if 10 <= district % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(district % 10, "th")
    district_ord = f"{district}{ord_suffix}" if district else "at-large"
    label = f"{state_name}'s {district_ord} Congressional District" if district else f"{state_name} (at-large)"

    return {
        "address": address.strip(),
        "lat": lat,
        "lng": lng,
        "state": state_abbrev,
        "district": district,
        "districtLabel": district_label,
        "stateName": state_name,
        "label": label,
    }


# FIPS state code to 2-letter abbreviation (Census returns FIPS)
_fips_to_abbrev = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT",
    "10": "DE", "11": "FL", "12": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
    "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD", "25": "MA",
    "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV",
    "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD", "47": "TN",
    "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
    "56": "WY", "72": "PR", "78": "VI", "66": "GU", "69": "MP", "60": "AS", "74": "UM",
}
