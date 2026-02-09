"""Ingest FEC data for cycles 2022, 2024, 2026. Use --sample for quick validation."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy.orm import Session

from config import CYCLES
from fec_client import (
    get_candidates,
    get_committees,
    get_schedule_a,
    get_totals_by_committee,
)
from schema import (
    Base,
    Candidate,
    Committee,
    Contribution,
    TotalByCommittee,
    get_engine,
    init_db,
)
from sqlalchemy import desc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def normalize_contributor_name(name: str | None) -> str:
    if not name:
        return ""
    s = re.sub(r"[^\w\s]", "", (name or "").lower())
    return " ".join(s.split())[:200]


def ingest_candidates(session: Session, cycle: int, max_pages: int | None = None) -> int:
    count = 0
    for office in ["P", "H", "S"]:
        for c in get_candidates(cycle=cycle, office=office, max_pages=max_pages):
            session.merge(
                Candidate(
                    candidate_id=c["candidate_id"],
                    cycle=cycle,
                    name=c.get("name"),
                    party_full=c.get("party_full"),
                    office=c.get("office"),
                    state=c.get("state"),
                    incumbent_challenge_full=c.get("incumbent_challenge_full"),
                )
            )
            count += 1
    return count


def ingest_committees(session: Session, cycle: int, max_pages: int | None = None) -> int:
    count = 0
    for co in get_committees(cycle=cycle, max_pages=max_pages):
        candidate_ids = json.dumps(co.get("candidate_ids") or [])
        session.merge(
            Committee(
                committee_id=co["committee_id"],
                cycle=cycle,
                name=co.get("name"),
                party_full=co.get("party_full"),
                committee_type=co.get("committee_type"),
                candidate_ids=candidate_ids,
            )
        )
        count += 1
    return count


def ingest_totals(session: Session, cycle: int, max_pages: int | None = None) -> int:
    count = 0
    for t in get_totals_by_committee(cycle, max_pages=max_pages):
        cids = t.get("sponsor_candidate_ids")
        candidate_id = cids[0] if isinstance(cids, list) and cids else None
        cov = t.get("coverage_end_date")
        coverage_end_date = str(cov)[:10] if cov else None
        session.merge(
            TotalByCommittee(
                cycle=cycle,
                committee_id=t.get("committee_id"),
                candidate_id=candidate_id,
                receipts=float(t.get("receipts") or 0),
                disbursements=float(t.get("disbursements") or 0),
                coverage_end_date=coverage_end_date,
            )
        )
        count += 1
    return count


def ingest_schedule_a(
    session: Session,
    cycle: int,
    *,
    max_contributions: int | None = None,
    committee_ids: list | None = None,
    max_pages: int | None = None,
) -> int:
    """Ingest Schedule A for cycle. If committee_ids given, pull per committee (API requires committee_id); else try cycle-only (may 400)."""
    count = 0
    if committee_ids:
        # API requires committee_id for Schedule A; pull per committee.
        for cid in committee_ids:
            if max_contributions and count >= max_contributions:
                break
            it = get_schedule_a(cycle=cycle, committee_id=cid, max_pages=max_pages)
            for rec in it:
                if max_contributions and count >= max_contributions:
                    break
                session.add(
                    Contribution(
                        cycle=cycle,
                        committee_id=rec.get("committee_id"),
                        candidate_id=rec.get("candidate_id"),
                        contributor_name=rec.get("contributor_name"),
                        contributor_street_1=rec.get("contributor_street_1"),
                        contributor_city=rec.get("contributor_city"),
                        contributor_state=rec.get("contributor_state"),
                        contributor_zip=rec.get("contributor_zip"),
                        contributor_employer=rec.get("contributor_employer"),
                        contributor_occupation=rec.get("contributor_occupation"),
                        contribution_receipt_date=rec.get("contribution_receipt_date"),
                        contribution_receipt_amount=float(rec.get("contribution_receipt_amount") or 0),
                        is_individual=1 if rec.get("is_individual") else 0,
                        two_year_transaction_period=rec.get("two_year_transaction_period") or cycle,
                    )
                )
                count += 1
                if count % 500 == 0:
                    session.commit()
        return count
    # Legacy: try cycle-only (OpenFEC may return 400)
    it = get_schedule_a(cycle=cycle, max_pages=max_pages)
    for rec in it:
        if max_contributions and count >= max_contributions:
            break
        session.add(
            Contribution(
                cycle=cycle,
                committee_id=rec.get("committee_id"),
                candidate_id=rec.get("candidate_id"),
                contributor_name=rec.get("contributor_name"),
                contributor_street_1=rec.get("contributor_street_1"),
                contributor_city=rec.get("contributor_city"),
                contributor_state=rec.get("contributor_state"),
                contributor_zip=rec.get("contributor_zip"),
                contributor_employer=rec.get("contributor_employer"),
                contributor_occupation=rec.get("contributor_occupation"),
                contribution_receipt_date=rec.get("contribution_receipt_date"),
                contribution_receipt_amount=float(rec.get("contribution_receipt_amount") or 0),
                is_individual=1 if rec.get("is_individual") else 0,
                two_year_transaction_period=rec.get("two_year_transaction_period") or cycle,
            )
        )
        count += 1
        if count % 500 == 0:
            session.commit()
    return count


def run(
    cycles: list | None = None,
    sample: bool = False,
    skip_schedule_a: bool = False,
    max_pages: int | None = None,
    top_committees: int | None = 20,
):
    cycles = cycles or CYCLES
    init_db()
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine, autoflush=False)
    session = SessionLocal()

    try:
        for cycle in cycles:
            print(f"Cycle {cycle}: candidates...")
            n = ingest_candidates(session, cycle, max_pages=max_pages)
            session.commit()
            print(f"  candidates: {n}")

            print(f"Cycle {cycle}: committees...")
            n = ingest_committees(session, cycle, max_pages=max_pages)
            session.commit()
            print(f"  committees: {n}")

            print(f"Cycle {cycle}: totals...")
            n = ingest_totals(session, cycle, max_pages=max_pages)
            session.commit()
            print(f"  totals: {n}")

            if skip_schedule_a:
                print(f"Cycle {cycle}: skipping Schedule A")
                continue
            # Schedule A requires committee_id; use top N committees by receipts.
            committee_ids = [
                r[0]
                for r in session.query(TotalByCommittee.committee_id)
                .filter(TotalByCommittee.cycle == cycle)
                .order_by(desc(TotalByCommittee.receipts))
                .limit(top_committees or 999)
                .all()
            ]
            max_contrib = 2000 if sample else None
            print(f"Cycle {cycle}: Schedule A (top {len(committee_ids)} committees, sample={sample}, max={max_contrib})...")
            n = ingest_schedule_a(
                session, cycle,
                committee_ids=committee_ids if committee_ids else None,
                max_contributions=max_contrib,
                max_pages=max_pages,
            )
            session.commit()
            print(f"  contributions: {n}")
    finally:
        session.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle", type=int, action="append", help="Cycle(s) to ingest (default: 2022, 2024, 2026)")
    ap.add_argument("--sample", action="store_true", help="Limit Schedule A to 2000 per cycle")
    ap.add_argument("--skip-schedule-a", action="store_true", help="Skip itemized contributions")
    ap.add_argument("--max-pages", type=int, default=None, help="Max API pages per endpoint (for DEMO_KEY)")
    ap.add_argument("--top-committees", type=int, default=20, help="For Schedule A: pull contributions for top N committees by receipts (default 20)")
    args = ap.parse_args()
    run(
        cycles=args.cycle or None,
        sample=args.sample,
        skip_schedule_a=args.skip_schedule_a,
        max_pages=args.max_pages,
        top_committees=args.top_committees,
    )
