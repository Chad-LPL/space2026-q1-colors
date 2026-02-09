"""One-time migration: add email_body and call_script to contact_scripts for existing DBs."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from schema import get_engine
from sqlalchemy import text

def main():
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(contact_scripts)"))
        columns = {row[1] for row in result}
        if "email_body" not in columns:
            conn.execute(text("ALTER TABLE contact_scripts ADD COLUMN email_body TEXT"))
            conn.commit()
            print("Added column email_body")
        else:
            print("Column email_body already exists")
        if "call_script" not in columns:
            conn.execute(text("ALTER TABLE contact_scripts ADD COLUMN call_script TEXT"))
            conn.commit()
            print("Added column call_script")
        else:
            print("Column call_script already exists")
    print("Migration done.")

if __name__ == "__main__":
    main()
