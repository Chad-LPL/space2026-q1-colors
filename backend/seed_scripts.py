"""Seed a few contact scripts for quick picks."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from schema import ContactScript, get_engine, init_db
from sqlalchemy.orm import sessionmaker

init_db()
engine = get_engine()
Session = sessionmaker(bind=engine)

SCRIPTS = [
    {
        "title": "Support climate action",
        "body": "I am a constituent and I'm writing to urge you to support strong climate legislation and clean energy investments. This is important to me and my family. Thank you.",
        "subject": "Support climate action",
        "issue_slug": "climate",
    },
    {
        "title": "Protect voting rights",
        "body": "I am a constituent and I'm calling to ask you to protect voting rights and oppose any legislation that makes it harder for Americans to vote. Thank you.",
        "subject": "Protect voting rights",
        "issue_slug": "voting-rights",
    },
    {
        "title": "Support affordable healthcare",
        "body": "I am a constituent and I'm writing to ask you to support affordable healthcare and lower prescription drug costs. Thank you.",
        "subject": "Support affordable healthcare",
        "issue_slug": "healthcare",
    },
]


def main():
    db = Session()
    for s in SCRIPTS:
        existing = db.query(ContactScript).filter(ContactScript.title == s["title"]).first()
        if not existing:
            db.add(ContactScript(**s))
    db.commit()
    print("Seeded", len(SCRIPTS), "contact scripts")
    db.close()


if __name__ == "__main__":
    main()
