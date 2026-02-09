"""OpenFEC API client. Rate limit: 1000/hour; 100 results per page max."""
from __future__ import annotations

import time

from typing import Any, Iterator

import httpx

from config import FEC_API_KEY, FEC_BASE_URL, PER_PAGE, RATE_LIMIT_DELAY

MAX_RETRIES = 5
INITIAL_BACKOFF = 10.0


def _get(path: str, params: dict | None = None) -> dict:
    params = dict(params or {})
    params.setdefault("api_key", FEC_API_KEY)
    params.setdefault("per_page", PER_PAGE)
    with httpx.Client(timeout=60) as client:
        last_exc = None
        for attempt in range(MAX_RETRIES):
            try:
                r = client.get(f"{FEC_BASE_URL}{path}", params=params)
                if r.status_code == 429:
                    last_exc = httpx.HTTPStatusError(
                        "Rate limited (429)", request=r.request, response=r
                    )
                    if attempt < MAX_RETRIES - 1:
                        backoff = INITIAL_BACKOFF * (2 ** attempt)
                        time.sleep(backoff)
                        continue
                    raise last_exc
                r.raise_for_status()
                return r.json()
            except httpx.HTTPStatusError as e:
                last_exc = e
                if e.response.status_code == 429 and attempt < MAX_RETRIES - 1:
                    backoff = INITIAL_BACKOFF * (2 ** attempt)
                    time.sleep(backoff)
                    continue
                raise
        if last_exc:
            raise last_exc
        raise RuntimeError("Unexpected _get exit")


def _paginate(path: str, params: dict | None = None, max_pages: int | None = None) -> Iterator[dict]:
    params = dict(params or {})
    page = 1
    while True:
        if max_pages and page > max_pages:
            break
        params["page"] = page
        data = _get(path, params)
        results = data.get("results") or []
        if not results:
            break
        for item in results:
            yield item
        if len(results) < params.get("per_page", PER_PAGE):
            break
        page += 1
        time.sleep(RATE_LIMIT_DELAY)


def get_candidates(cycle: int, office: str | None = None, max_pages: int | None = None) -> list[dict]:
    """Fetch candidates for a cycle. office: 'P' (president), 'H', 'S'."""
    params = {"cycle": cycle}
    if office:
        params["office"] = office
    return list(_paginate("/candidates/", params, max_pages=max_pages))


def get_committees(cycle: int, candidate_id: str | None = None, max_pages: int | None = None) -> list[dict]:
    """Fetch committees for a cycle, optionally for one candidate."""
    params = {"cycle": cycle}
    if candidate_id:
        params["candidate_id"] = candidate_id
    return list(_paginate("/committees/", params, max_pages=max_pages))


def get_totals_by_committee(cycle: int, max_pages: int | None = None) -> list[dict]:
    """Fetch committee totals for a cycle."""
    return list(_paginate("/totals/by_committee/", {"cycle": cycle}, max_pages=max_pages))


def get_schedule_a(
    cycle: int,
    committee_id: str | None = None,
    min_date: str | None = None,
    max_date: str | None = None,
    max_pages: int | None = None,
) -> Iterator[dict]:
    """Itemized receipts (Schedule A). Use committee_id to scope or pull all for cycle."""
    params = {"cycle": cycle}
    if committee_id:
        params["committee_id"] = committee_id
    if min_date:
        params["min_date"] = min_date
    if max_date:
        params["max_date"] = max_date
    return _paginate("/schedules/schedule_a/", params, max_pages=max_pages)
