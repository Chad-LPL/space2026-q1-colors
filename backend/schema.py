"""
Schema for Congress Map: contact scripts, contact events (stats), optional cache.
"""
from pathlib import Path

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

from config import DB_PATH

Base = declarative_base()


def get_engine():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{DB_PATH}", echo=False)


class ContactScript(Base):
    """Seed/curated scripts for quick picks (optional)."""
    __tablename__ = "contact_scripts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    subject = Column(String(255))
    bill_id = Column(String(50), index=True)
    issue_slug = Column(String(100), index=True)
    email_body = Column(Text)   # full email for library; when set, /scripts/generate returns this instead of calling LLM
    call_script = Column(Text)  # full phone script for library


class ContactEvent(Base):
    """One contact event: user contacted member about issue (for weekly/monthly stats). No PII."""
    __tablename__ = "contact_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(String(20), nullable=False, index=True)  # bioguide or Congress API id
    issue_id = Column(String(100), index=True)   # bill number or topic slug
    topic = Column(String(255), index=True)      # free-text topic if no bill
    contact_type = Column(String(10), nullable=False, default="email")  # email | call
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    init_db()
