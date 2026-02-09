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
    issueTitle: Optional[str] = None  # e.g. seed script title for LLM context
    scriptId: Optional[int] = None  # seed script id; backend can look up title/issueSlug/billId
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


def _generate_script_gemini(
    member_name: str,
    member_state: Optional[str],
    member_party: Optional[str],
    topic: str,
) -> Optional[dict]:
    """Call Gemini to generate email body, call script, and subject. Returns dict or None on failure."""
    import re
    from config import GEMINI_API_KEY
    if not GEMINI_API_KEY or not topic.strip():
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")
        state_line = f", State: {member_state}" if member_state else ""
        party_line = f", Party: {member_party}" if member_party else ""
        prompt = f"""You are helping a constituent write to their member of Congress. Write from a left-leaning, progressive perspective: the tone and policy stance should reflect progressive values (e.g. climate action, healthcare access, voting rights, economic fairness, civil rights).

Member: {member_name}{state_line}{party_line}
Topic/issue the constituent cares about: {topic}

Respond with exactly three sections, no other text before or after:

SUBJECT: (one short subject line for the email, under 80 chars)

EMAIL:
(2-3 short paragraphs: say you are a constituent, state what you want them to support or oppose, briefly why it matters to you, and a polite closing.)

CALL_SCRIPT:
(A short phone script: intro e.g. "Hi, I'm a constituent from [state]." Then the main ask in 1-2 sentences. End with e.g. "Thank you for your time.")"""
        response = model.generate_content(prompt)
        if not response or not response.text:
            return None
        text = response.text.strip()
        subject = "Constituent request"
        email_body = ""
        call_script = ""
        if "SUBJECT:" in text:
            subj_match = re.search(r"SUBJECT:\s*(.+?)(?=\n\n|\nEMAIL:|\Z)", text, re.DOTALL | re.IGNORECASE)
            if subj_match:
                subject = subj_match.group(1).strip().split("\n")[0].strip() or subject
        if "EMAIL:" in text and "CALL_SCRIPT:" in text:
            email_match = re.search(r"EMAIL:\s*(.+?)CALL_SCRIPT:", text, re.DOTALL | re.IGNORECASE)
            call_match = re.search(r"CALL_SCRIPT:\s*(.+)$", text, re.DOTALL | re.IGNORECASE)
            if email_match:
                email_body = email_match.group(1).strip()
            if call_match:
                call_script = call_match.group(1).strip()
        if not email_body or not call_script:
            return None
        return {"emailBody": email_body, "callScript": call_script, "subject": subject}
    except Exception as e:
        import logging
        logging.warning("Gemini script generation failed: %s", e)
        return None


@app.post("/scripts/generate")
def script_generate(body: ScriptGenerateRequest, db: Session = Depends(get_db)):
    """Generate script via LLM (Gemini preferred). Without LLM key, returns placeholder."""
    from config import GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY
    placeholder = {
        "emailBody": "I am a constituent and I'm writing to ask you to support [describe the issue]. Thank you.",
        "callScript": "Hi, I'm a constituent. I'm calling to ask you to support [describe the issue]. Thank you.",
        "subject": "Constituent request",
    }
    no_llm_message = "LLM not configured; using placeholder. Add GEMINI_API_KEY (free at https://aistudio.google.com/app/apikey) for AI-generated scripts."
    if not GEMINI_API_KEY and not OPENAI_API_KEY and not ANTHROPIC_API_KEY:
        return {**placeholder, "message": no_llm_message}

    topic = (body.issueText or "").strip()
    if not topic and (body.issueTitle or body.issueOrBillId):
        topic = (body.issueTitle or body.issueOrBillId or "").strip()
    if not topic and body.scriptId:
        row = db.query(ContactScript).filter(ContactScript.id == body.scriptId).first()
        if row:
            topic = (row.title or row.issue_slug or row.bill_id or "this issue").strip()

    member_name = "your representative"
    member_state = None
    member_party = None
    if body.memberId:
        m = get_member(body.memberId)
        if m:
            member_name = m.get("name") or member_name
            member_state = m.get("state")
            member_party = m.get("party")

    if GEMINI_API_KEY and topic:
        result = _generate_script_gemini(member_name, member_state, member_party, topic)
        if result:
            return result
        return {**placeholder, "message": "Generation failed; rate limit or API error. Try again in a moment."}
    if GEMINI_API_KEY and not topic:
        return {**placeholder, "message": "Enter an issue or pick a topic above, then click Generate script."}
    return {**placeholder, "message": no_llm_message}


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
