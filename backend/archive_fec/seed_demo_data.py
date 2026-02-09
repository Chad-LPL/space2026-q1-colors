"""
Seed minimal demo data so the app and frontend work without hitting the FEC API.
Run: python3 seed_demo_data.py
Then start the API (aggregates are built automatically).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from schema import (
    Candidate,
    Committee,
    Contribution,
    TotalByCommittee,
    get_engine,
    init_db,
)
from sqlalchemy.orm import sessionmaker
from aggregates import build_receipts_by_month, build_receipts_by_state

init_db()
engine = get_engine()
Session = sessionmaker(bind=engine)
session = Session()

# Cycles
CYCLES = [2022, 2024]

def seed():
    # Candidates 2024 (president, house, senate)
    for cid, name, party, office in [
        ("P80001571", "Joseph R Biden Jr", "DEMOCRAT", "P"),
        ("P80002735", "Donald J Trump", "REPUBLICAN", "P"),
        ("H0CA45143", "Nancy Pelosi", "DEMOCRAT", "H"),
        ("S0CA00955", "Alex Padilla", "DEMOCRAT", "S"),
    ]:
        for cycle in CYCLES:
            session.merge(Candidate(candidate_id=cid, cycle=cycle, name=name, party_full=party, office=office, state="CA" if office != "P" else None, incumbent_challenge_full=None))

    # Committees 2024
    for coid, name, party in [
        ("C00703975", "BIDEN FOR PRESIDENT", "DEMOCRAT"),
        ("C00580100", "DONALD J. TRUMP FOR PRESIDENT, INC.", "REPUBLICAN"),
        ("C00694323", "Nancy Pelosi for Congress", "DEMOCRAT"),
    ]:
        for cycle in CYCLES:
            session.merge(Committee(committee_id=coid, cycle=cycle, name=name, party_full=party, committee_type="O", candidate_ids="[]"))

    # Totals
    for cycle in CYCLES:
        session.merge(TotalByCommittee(cycle=cycle, committee_id="C00703975", candidate_id="P80001571", receipts=500_000_000, disbursements=400_000_000, coverage_end_date="2024-12-31"))
        session.merge(TotalByCommittee(cycle=cycle, committee_id="C00580100", candidate_id="P80002735", receipts=450_000_000, disbursements=420_000_000, coverage_end_date="2024-12-31"))
        session.merge(TotalByCommittee(cycle=cycle, committee_id="C00694323", candidate_id="H0CA45143", receipts=20_000_000, disbursements=18_000_000, coverage_end_date="2024-12-31"))

    # Contributions (Schedule A) - 2022 and 2024 so we have first-time mega-donors and double givers
    contribs_2024 = [
        ("Alice Smith", "123 Main St", "San Francisco", "CA", "94102", "Acme Corp", 15000, "2024-06-01", "C00703975", "P80001571"),
        ("Bob Jones", "456 Oak Ave", "Houston", "TX", "77001", "Jones LLC", 25000, "2024-07-15", "C00580100", "P80002735"),
        ("Carol White", "789 Elm St", "Chicago", "IL", "60601", "White & Co", 500, "2024-03-01", "C00703975", "P80001571"),
        ("Carol White", "789 Elm St", "Chicago", "IL", "60601", "White & Co", 600, "2024-08-01", "C00580100", "P80002735"),  # double giver
        ("David Lee", "321 Pine Rd", "Seattle", "WA", "98101", "Tech Inc", 12000, "2024-05-01", "C00703975", "P80001571"),  # first-time mega (no 2022)
        ("Eve Brown", "555 Cedar Ln", "Boston", "MA", "02101", "Acme Corp", 100, "2024-02-01", "C00694323", "H0CA45143"),
        ("Eve Brown", "555 Cedar Ln", "Boston", "MA", "02101", "Acme Corp", 100, "2024-04-01", "C00694323", "H0CA45143"),
        ("Eve Brown", "555 Cedar Ln", "Boston", "MA", "02101", "Acme Corp", 100, "2024-06-01", "C00694323", "H0CA45143"),  # address cluster
        ("Frank Davis", "555 Cedar Ln", "Boston", "MA", "02101", "Acme Corp", 200, "2024-03-15", "C00694323", "H0CA45143"),
        ("Grace Wilson", "555 Cedar Ln", "Boston", "MA", "02101", "Acme Corp", 150, "2024-07-01", "C00694323", "H0CA45143"),
    ]
    for name, street, city, state, zip_, employer, amount, date, committee_id, candidate_id in contribs_2024:
        session.add(Contribution(
            cycle=2024, committee_id=committee_id, candidate_id=candidate_id,
            contributor_name=name, contributor_street_1=street, contributor_city=city,
            contributor_state=state, contributor_zip=zip_, contributor_employer=employer,
            contributor_occupation=None, contribution_receipt_date=date,
            contribution_receipt_amount=amount, is_individual=1, two_year_transaction_period=2024,
        ))
    # 2022: a few so Carol White and Bob have prior cycle; David Lee has none (first-time mega)
    session.add(Contribution(cycle=2022, committee_id="C00703975", candidate_id="P80001571", contributor_name="Carol White", contributor_street_1="789 Elm St", contributor_city="Chicago", contributor_state="IL", contributor_zip="60601", contributor_employer="White & Co", contributor_occupation=None, contribution_receipt_date="2022-05-01", contribution_receipt_amount=300, is_individual=1, two_year_transaction_period=2022))
    session.add(Contribution(cycle=2022, committee_id="C00580100", candidate_id="P80002735", contributor_name="Bob Jones", contributor_street_1="456 Oak Ave", contributor_city="Houston", contributor_state="TX", contributor_zip="77001", contributor_employer="Jones LLC", contributor_occupation=None, contribution_receipt_date="2022-06-01", contribution_receipt_amount=1000, is_individual=1, two_year_transaction_period=2022))

    session.commit()
    print("Demo data seeded.")
    # Build aggregates so receipts-by-month and receipts-by-state charts have data
    for cycle in CYCLES:
        build_receipts_by_month(session, cycle)
        session.commit()
        build_receipts_by_state(session, cycle)
        session.commit()
    print("Aggregates built.")


if __name__ == "__main__":
    seed()
