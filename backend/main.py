"""
Congress Map API: geocode, members, scripts, contact events, districts.
"""
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import CONGRESS_API_KEY, CURRENT_CONGRESS
from congress_client import (
    get_member,
    get_member_bills,
    get_member_votes,
    get_members_for_district,
)
from geocoder import geocode
from schema import ContactEvent, ContactScript, get_engine, init_db
from sqlalchemy.orm import sessionmaker

init_db()
engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI(title="Congress Map API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Request/response models ----------
class ContactEventCreate(BaseModel):
    memberId: str
    issueId: Optional[str] = None
    topic: Optional[str] = None
    contactType: str  # "email" | "call"


class ScriptGenerateRequest(BaseModel):
    memberId: str
    issueOrBillId: Optional[str] = None
    issueText: Optional[str] = None
    format: Optional[str] = None  # "email" | "call"


# ---------- Health ----------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/debug/congress-api")
def debug_congress_api():
    """Verify CONGRESS_API_KEY is loaded and Congress API responds. Useful when member data is missing."""
    key_loaded = bool(CONGRESS_API_KEY)
    key_preview = ""
    if key_loaded:
        k = CONGRESS_API_KEY.strip()
        key_preview = f"{k[:4]}...{k[-4:]}" if len(k) >= 8 else "set"
    test_ok = False
    test_error = None
    if key_loaded:
        try:
            data = get_members_for_district("IL", 10)
            rep = data.get("representative")
            senators = data.get("senators") or []
            test_ok = rep is not None or len(senators) > 0
            if not test_ok:
                test_error = "API responded but returned no members for IL-10 (key may be invalid or rate-limited)."
        except Exception as e:
            test_error = str(e)
    return {
        "congress_api_key_loaded": key_loaded,
        "congress_api_key_preview": key_preview if key_loaded else None,
        "test_request_ok": test_ok,
        "test_error": test_error,
    }


# ---------- Geocode ----------
@app.get("/geocode")
def geocode_endpoint(address: str = Query(..., min_length=1)):
    result = geocode(address)
    if result is None:
        return {"error": "Address not found", "address": address}
    return result


@app.get("/geocode/suggest")
def geocode_suggest_endpoint(address: str = Query(""), limit: int = Query(5, ge=1, le=10)):
    from geocoder import geocode_suggest
    suggestions = geocode_suggest(address, limit=limit)
    return {"suggestions": suggestions}


# ---------- Districts (GeoJSON) ----------
@app.get("/districts/geojson")
def districts_geojson():
    """Serve 118th/119th Congress district boundaries. Run backend/scripts/fetch_districts_118.py to create."""
    static_dir = Path(__file__).resolve().parent / "static"
    for name in ("districts_119.geojson", "districts_118.geojson"):
        p = static_dir / name
        if p.exists():
            return FileResponse(
                p,
                media_type="application/geo+json",
                headers={"Cache-Control": "no-store"},
            )
    return {"error": "District GeoJSON not yet available", "hint": "Run: python backend/scripts/fetch_districts_118.py"}


# ---------- Members ----------
@app.get("/members")
def members(state: str = Query(..., min_length=2), district: int = Query(..., ge=0)):
    if not CONGRESS_API_KEY:
        return {"error": "CONGRESS_API_KEY not configured"}
    state = state.upper()[:2]
    data = get_members_for_district(state, district)
    # When key is set but Congress API returned no members, surface a clear message (not "add key")
    if (
        data
        and data.get("representative") is None
        and not data.get("senators")
        and CONGRESS_API_KEY
    ):
        data["membersError"] = (
            "Congress API returned no members for this district. "
            "Check your key at api.data.gov or try again later."
        )
    return data


@app.get("/members/{member_id}")
def member_detail(member_id: str):
    if not CONGRESS_API_KEY:
        return {"error": "CONGRESS_API_KEY not configured"}
    m = get_member(member_id)
    if m is None:
        return {"error": "Member not found", "id": member_id}
    return m


@app.get("/members/{member_id}/bills")
def member_bills(member_id: str, limit: int = Query(20, le=50)):
    if not CONGRESS_API_KEY:
        return {"error": "CONGRESS_API_KEY not configured"}
    bills = get_member_bills(member_id, limit=limit)
    return {"memberId": member_id, "bills": bills}


@app.get("/members/{member_id}/votes")
def member_votes(member_id: str, limit: int = Query(20, le=50)):
    if not CONGRESS_API_KEY:
        return {"error": "CONGRESS_API_KEY not configured"}
    votes = get_member_votes(member_id, limit=limit)
    return {"memberId": member_id, "votes": votes}


# ---------- Scripts (seed list; generate is stubbed without LLM) ----------
@app.get("/scripts")
def scripts_list(db: Session = Depends(get_db)):
    rows = db.query(ContactScript).order_by(ContactScript.id).all()
    return {
        "scripts": [
            {"id": r.id, "title": r.title, "billId": r.bill_id, "issueSlug": r.issue_slug}
            for r in rows
        ]
    }


@app.get("/scripts/{script_id}")
def script_get(script_id: int, db: Session = Depends(get_db)):
    r = db.query(ContactScript).filter(ContactScript.id == script_id).first()
    if r is None:
        return {"error": "Script not found", "id": script_id}
    return {"id": r.id, "title": r.title, "body": r.body, "subject": r.subject, "billId": r.bill_id, "issueSlug": r.issue_slug}


@app.post("/scripts/generate")
def script_generate(body: ScriptGenerateRequest):
    """Generate script via LLM. Without LLM key, returns placeholder message."""
    from config import OPENAI_API_KEY, ANTHROPIC_API_KEY
    if not OPENAI_API_KEY and not ANTHROPIC_API_KEY:
        return {
            "emailBody": "I am a constituent and I'm writing to ask you to support [describe the issue]. Thank you.",
            "callScript": "Hi, I'm a constituent. I'm calling to ask you to support [describe the issue]. Thank you.",
            "subject": "Constituent request",
            "message": "LLM not configured; using placeholder. Add OPENAI_API_KEY or ANTHROPIC_API_KEY for AI-generated scripts.",
        }
    # TODO: call OpenAI or Anthropic with member + issue, return generated text
    return {
        "emailBody": "I am a constituent and I'm writing to ask you to support [describe the issue]. Thank you.",
        "callScript": "Hi, I'm a constituent. I'm calling to ask you to support [describe the issue]. Thank you.",
        "subject": "Constituent request",
    }


# ---------- Contact events (stats) ----------
@app.post("/contact-events")
def contact_events_create(body: ContactEventCreate, db: Session = Depends(get_db)):
    db.add(
        ContactEvent(
            member_id=body.memberId,
            issue_id=body.issueId,
            topic=body.topic,
            contact_type=body.contactType.lower() if body.contactType else "email",
        )
    )
    db.commit()
    return {"ok": True}


@app.get("/contact-stats")
def contact_stats(
    memberId: str = Query(...),
    issueId: str = Query(None),
    topic: str = Query(None),
    db: Session = Depends(get_db),
):
    """Return count of contact events for this member + issue in last 7 and 30 days."""
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    q = db.query(ContactEvent).filter(ContactEvent.member_id == memberId)
    if issueId:
        q = q.filter(ContactEvent.issue_id == issueId)
    if topic:
        q = q.filter(ContactEvent.topic == topic)

    last7 = q.filter(ContactEvent.created_at >= week_ago).count()
    last30 = q.filter(ContactEvent.created_at >= month_ago).count()
    return {"memberId": memberId, "issueId": issueId, "topic": topic, "last7Days": last7, "last30Days": last30}
