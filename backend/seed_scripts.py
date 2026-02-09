"""Seed the contact script library (50 topics with full email and call scripts)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from schema import ContactScript, get_engine, init_db
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from script_library import SCRIPT_LIBRARY

init_db()
engine = get_engine()
Session = sessionmaker(bind=engine)


def ensure_columns():
    """Add email_body and call_script if missing (for existing DBs)."""
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(contact_scripts)"))
        columns = {row[1] for row in result}
        if "email_body" not in columns:
            conn.execute(text("ALTER TABLE contact_scripts ADD COLUMN email_body TEXT"))
        if "call_script" not in columns:
            conn.execute(text("ALTER TABLE contact_scripts ADD COLUMN call_script TEXT"))
        conn.commit()


def main():
    ensure_columns()
    db = Session()
    count = 0
    for s in SCRIPT_LIBRARY:
        existing = db.query(ContactScript).filter(ContactScript.issue_slug == s["issue_slug"]).first()
        if existing:
            existing.title = s["title"]
            existing.body = s["body"]
            existing.subject = s["subject"]
            existing.email_body = s["email_body"]
            existing.call_script = s["call_script"]
        else:
            db.add(ContactScript(
                title=s["title"],
                issue_slug=s["issue_slug"],
                subject=s["subject"],
                body=s["body"],
                email_body=s["email_body"],
                call_script=s["call_script"],
            ))
        count += 1
    db.commit()
    print("Seeded", count, "contact scripts (library)")
    db.close()


if __name__ == "__main__":
    main()
