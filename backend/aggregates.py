"""Build aggregates from contributions: receipts by month, receipts by state."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import case, func, text
from sqlalchemy.orm import Session

from schema import (
    Contribution,
    ReceiptsByMonth,
    ReceiptsByState,
    get_engine,
    init_db,
)
from sqlalchemy.orm import sessionmaker


def build_receipts_by_month(session: Session, cycle: int) -> int:
    """Aggregate contributions by (cycle, committee_id, candidate_id, year_month); small vs large donor."""
    session.execute(
        text("DELETE FROM receipts_by_month WHERE cycle = :cycle"),
        {"cycle": cycle},
    )
    # contribution_receipt_date is YYYY-MM-DD; use first 7 chars for year_month
    q = (
        session.query(
            Contribution.cycle,
            Contribution.committee_id,
            Contribution.candidate_id,
            func.substr(Contribution.contribution_receipt_date, 1, 7).label("year_month"),
            func.sum(Contribution.contribution_receipt_amount).label("total"),
            func.sum(
                case(
                    (Contribution.contribution_receipt_amount < 200, Contribution.contribution_receipt_amount),
                    else_=0,
                )
            ).label("small_donor_total"),
            func.sum(
                case(
                    (Contribution.contribution_receipt_amount >= 200, Contribution.contribution_receipt_amount),
                    else_=0,
                )
            ).label("large_donor_total"),
        )
        .filter(Contribution.cycle == cycle)
        .filter(Contribution.contribution_receipt_date != None)
        .group_by(
            Contribution.cycle,
            Contribution.committee_id,
            Contribution.candidate_id,
            func.substr(Contribution.contribution_receipt_date, 1, 7),
        )
    )
    count = 0
    for row in q:
        session.add(
            ReceiptsByMonth(
                cycle=row.cycle,
                committee_id=row.committee_id,
                candidate_id=row.candidate_id,
                year_month=row.year_month,
                total=float(row.total or 0),
                small_donor_total=float(row.small_donor_total or 0),
                large_donor_total=float(row.large_donor_total or 0),
            )
        )
        count += 1
    return count


def build_receipts_by_state(session: Session, cycle: int) -> int:
    """Aggregate contributions by (cycle, committee_id, candidate_id, state)."""
    session.execute(
        text("DELETE FROM receipts_by_state WHERE cycle = :cycle"),
        {"cycle": cycle},
    )
    q = (
        session.query(
            Contribution.cycle,
            Contribution.committee_id,
            Contribution.candidate_id,
            Contribution.contributor_state,
            func.sum(Contribution.contribution_receipt_amount).label("total"),
        )
        .filter(Contribution.cycle == cycle)
        .filter(Contribution.contributor_state != None)
        .filter(Contribution.contributor_state != "")
        .group_by(
            Contribution.cycle,
            Contribution.committee_id,
            Contribution.candidate_id,
            Contribution.contributor_state,
        )
    )
    count = 0
    for row in q:
        session.add(
            ReceiptsByState(
                cycle=row.cycle,
                committee_id=row.committee_id,
                candidate_id=row.candidate_id,
                state=row.contributor_state,
                total=float(row.total or 0),
            )
        )
        count += 1
    return count


def run(cycles: list | None = None):
    from config import CYCLES
    cycles = cycles or CYCLES
    init_db()
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        for cycle in cycles:
            print(f"Cycle {cycle}: receipts_by_month...")
            n = build_receipts_by_month(session, cycle)
            session.commit()
            print(f"  rows: {n}")
            print(f"Cycle {cycle}: receipts_by_state...")
            n = build_receipts_by_state(session, cycle)
            session.commit()
            print(f"  rows: {n}")
    finally:
        session.close()


if __name__ == "__main__":
    run()
