"""Story detectors: first-time mega-donors, double givers, address/employer clusters."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from schema import Candidate, Committee, Contribution, get_engine, init_db
from sqlalchemy.orm import sessionmaker


def normalize_contributor_key(name: str | None, zip_code: str | None) -> str:
    """Normalize for contributor identity: lowercase, strip punctuation, name + zip."""
    n = (name or "").lower()
    n = re.sub(r"[^\w\s]", "", n)
    n = " ".join(n.split())[:100]
    z = (zip_code or "")[:5] if zip_code else ""
    return f"{n}|{z}"


def first_time_mega_donors(
    session: Session,
    cycle: int,
    *,
    prior_cycle: int | None = None,
    min_amount: float = 10_000,
    max_prior_amount: float = 500,
    office: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Contributors in cycle with total > min_amount and prior cycle total < max_prior_amount.
    prior_cycle defaults to cycle - 2 (e.g. 2024 -> 2022).
    """
    if prior_cycle is None:
        prior_cycle = cycle - 2
    # Aggregate by normalized (name, zip) per cycle
    contrib_key = func.lower(
        func.trim(
            func.replace(
                func.replace(Contribution.contributor_name, ",", ""),
                ".",
                "",
            )
        )
    )
    # Simpler: group by name + zip
    subq_curr = (
        session.query(
            Contribution.contributor_name,
            Contribution.contributor_zip,
            func.sum(Contribution.contribution_receipt_amount).label("total"),
        )
        .filter(Contribution.cycle == cycle)
        .filter(Contribution.contributor_name != None)
        .filter(Contribution.contributor_name != "")
        .group_by(Contribution.contributor_name, Contribution.contributor_zip)
        .subquery()
    )
    subq_prior = (
        session.query(
            Contribution.contributor_name,
            Contribution.contributor_zip,
            func.sum(Contribution.contribution_receipt_amount).label("total"),
        )
        .filter(Contribution.cycle == prior_cycle)
        .filter(Contribution.contributor_name != None)
        .filter(Contribution.contributor_name != "")
        .group_by(Contribution.contributor_name, Contribution.contributor_zip)
        .subquery()
    )
    # Join: current total > min_amount, (prior total < max_prior_amount or no prior record)
    q = (
        session.query(
            subq_curr.c.contributor_name,
            subq_curr.c.contributor_zip,
            subq_curr.c.total,
        )
        .outerjoin(
            subq_prior,
            (subq_curr.c.contributor_name == subq_prior.c.contributor_name)
            & (subq_curr.c.contributor_zip == subq_prior.c.contributor_zip),
        )
        .filter(subq_curr.c.total >= min_amount)
        .filter(
            or_(
                subq_prior.c.total == None,
                subq_prior.c.total <= max_prior_amount,
            )
        )
        .order_by(subq_curr.c.total.desc())
        .limit(limit)
    )
    rows = q.all()
    return [
        {
            "contributor_name": r.contributor_name,
            "contributor_zip": r.contributor_zip,
            "cycle_total": float(r.total),
            "cycle": cycle,
            "prior_cycle": prior_cycle,
        }
        for r in rows
    ]


def double_givers(
    session: Session,
    cycle: int,
    *,
    min_amount_each_side: float = 500,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Contributors who gave >= min_amount_each_side to committees/candidates associated with both D and R.
    Map committee/candidate to party via Committee.party_full or Candidate.party_full.
    """
    # Get contributor -> list of (party, amount). Party from committee or candidate.
    # Contribution has committee_id, candidate_id. Committee has party_full; Candidate has party_full.
    # Aggregate by contributor (name, zip) and party; then find contributors with both D and R.
    subq = (
        session.query(
            Contribution.contributor_name,
            Contribution.contributor_zip,
            Committee.party_full,
            func.sum(Contribution.contribution_receipt_amount).label("total"),
        )
        .join(Committee, (Contribution.committee_id == Committee.committee_id) & (Contribution.cycle == Committee.cycle))
        .filter(Contribution.cycle == cycle)
        .filter(Contribution.contributor_name != None)
        .filter(Committee.party_full != None)
        .filter(Committee.party_full != "")
        .group_by(
            Contribution.contributor_name,
            Contribution.contributor_zip,
            Committee.party_full,
        )
        .subquery()
    )
    # Pivot: we need contributors who have both a D row and an R row with total >= min.
    dem = (
        session.query(subq.c.contributor_name, subq.c.contributor_zip, subq.c.total)
        .filter(func.upper(subq.c.party_full).contains("DEMOCRAT"))
        .subquery()
    )
    rep = (
        session.query(subq.c.contributor_name, subq.c.contributor_zip, subq.c.total)
        .filter(func.upper(subq.c.party_full).contains("REPUBLICAN"))
        .subquery()
    )
    q = (
        session.query(
            dem.c.contributor_name,
            dem.c.contributor_zip,
            dem.c.total.label("dem_total"),
            rep.c.total.label("rep_total"),
        )
        .join(
            rep,
            (dem.c.contributor_name == rep.c.contributor_name) & (dem.c.contributor_zip == rep.c.contributor_zip),
        )
        .filter(dem.c.total >= min_amount_each_side)
        .filter(rep.c.total >= min_amount_each_side)
        .order_by((dem.c.total + rep.c.total).desc())
        .limit(limit)
    )
    rows = q.all()
    return [
        {
            "contributor_name": r.contributor_name,
            "contributor_zip": r.contributor_zip,
            "dem_total": float(r.dem_total),
            "rep_total": float(r.rep_total),
            "cycle": cycle,
        }
        for r in rows
    ]


def clusters(
    session: Session,
    cycle: int,
    *,
    by: str = "address",  # "address" or "employer"
    min_contributions: int = 5,
    min_total: float = 10_000,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Group by contributor_zip + contributor_street_1 (or employer); flag high concentration.
    """
    if by == "employer":
        group = [Contribution.contributor_employer]
        label_name = "contributor_employer"
    else:
        group = [Contribution.contributor_zip, Contribution.contributor_street_1]
        label_name = "address"

    q = (
        session.query(
            *group,
            func.count(Contribution.id).label("num_contributions"),
            func.sum(Contribution.contribution_receipt_amount).label("total"),
        )
        .filter(Contribution.cycle == cycle)
    )
    if by == "employer":
        q = q.filter(Contribution.contributor_employer != None).filter(Contribution.contributor_employer != "")
    else:
        q = (
            q.filter(Contribution.contributor_zip != None)
            .filter(Contribution.contributor_zip != "")
            .filter(Contribution.contributor_street_1 != None)
            .filter(Contribution.contributor_street_1 != "")
        )
    q = (
        q.group_by(*group)
        .having(func.count(Contribution.id) >= min_contributions)
        .having(func.sum(Contribution.contribution_receipt_amount) >= min_total)
        .order_by(func.sum(Contribution.contribution_receipt_amount).desc())
        .limit(limit)
    )
    rows = q.all()
    if by == "employer":
        return [
            {
                "employer": r.contributor_employer,
                "num_contributions": r.num_contributions,
                "total": float(r.total),
                "cycle": cycle,
            }
            for r in rows
        ]
    return [
        {
            "contributor_zip": r.contributor_zip,
            "contributor_street_1": r.contributor_street_1,
            "num_contributions": r.num_contributions,
            "total": float(r.total),
            "cycle": cycle,
        }
        for r in rows
    ]


def get_all_stories(
    session: Session,
    cycle: int,
    *,
    office: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Return all three story types for a cycle."""
    return {
        "first_time_mega_donors": first_time_mega_donors(session, cycle, office=office),
        "double_givers": double_givers(session, cycle),
        "clusters_by_address": clusters(session, cycle, by="address"),
        "clusters_by_employer": clusters(session, cycle, by="employer"),
    }
