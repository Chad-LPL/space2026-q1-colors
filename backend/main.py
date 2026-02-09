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
    model_config = {"populate_by_name": True}
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


@app.get("/debug/gemini")
def debug_gemini(test: bool = Query(False, description="If true, call Gemini once to verify key and quota")):
    """Check if GEMINI_API_KEY is set and optionally test one Gemini call. Helps debug script generation failures."""
    from config import GEMINI_API_KEY
    key_loaded = bool(GEMINI_API_KEY and GEMINI_API_KEY.strip())
    key_preview = ""
    if key_loaded:
        k = (GEMINI_API_KEY or "").strip()
        key_preview = f"{k[:4]}...{k[-4:]}" if len(k) >= 8 else "set"
    test_ok = None
    test_error = None
    if key_loaded and test:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-2.0-flash")
            r = model.generate_content("Say hello in one word.")
            if getattr(r, "text", None) and r.text.strip():
                test_ok = True
            else:
                test_ok = False
                test_error = "Empty or blocked response"
        except Exception as e:
            test_ok = False
            test_error = _sanitize_error_for_user(str(e), max_len=200)
    return {
        "gemini_key_loaded": key_loaded,
        "gemini_key_preview": key_preview if key_loaded else None,
        "test_request_ok": test_ok,
        "test_error": test_error,
    }


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


def _sanitize_error_for_user(msg: str, max_len: int = 120) -> str:
    """Remove anything that could be an API key or token; truncate."""
    if not msg:
        return ""
    # Remove substrings that look like keys (long alphanumeric stretches)
    import re
    out = re.sub(r"\b[A-Za-z0-9_-]{30,}\b", "[REDACTED]", msg)
    return out.strip()[:max_len]


def _generate_script_gemini(
    member_name: str,
    member_state: Optional[str],
    member_party: Optional[str],
    topic: str,
) -> tuple[Optional[dict], Optional[str], Optional[str]]:
    """Call Gemini to generate email body, call script, and subject. Returns (result_dict, None, None) or (None, hint, detail) on failure."""
    import re
    from config import GEMINI_API_KEY
    if not GEMINI_API_KEY or not topic.strip():
        return None, None, None
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
        if not response:
            return None, "API returned no response", None
        if not getattr(response, "text", None) or not response.text.strip():
            import logging
            fb = getattr(response, "prompt_feedback", None)
            logging.warning("Gemini returned empty or blocked response: %s", fb)
            hint = "blocked or empty response"
            if fb and getattr(fb, "block_reason", None):
                hint = str(getattr(fb, "block_reason", hint))
            return None, hint, None
        text = response.text.strip()
        subject = "Constituent request"
        email_body = ""
        call_script = ""
        # Case-insensitive section headers; allow "Email" or "EMAIL", etc.
        if re.search(r"SUBJECT\s*:", text, re.IGNORECASE):
            subj_match = re.search(
                r"SUBJECT\s*:\s*(.+?)(?=\n\s*\n|\n\s*EMAIL\s*:|\n\s*CALL_SCRIPT\s*:|\Z)",
                text, re.DOTALL | re.IGNORECASE
            )
            if subj_match:
                subject = subj_match.group(1).strip().split("\n")[0].strip() or subject
        email_match = re.search(
            r"EMAIL\s*:\s*(.+?)(?=CALL_SCRIPT\s*:|\Z)",
            text, re.DOTALL | re.IGNORECASE
        )
        call_match = re.search(
            r"CALL_SCRIPT\s*:\s*(.+)$",
            text, re.DOTALL | re.IGNORECASE
        )
        if email_match:
            email_body = email_match.group(1).strip()
        if call_match:
            call_script = call_match.group(1).strip()
        # Fallback: if model returned prose without strict headers, use first 2 paragraphs as email, rest as call
        if (not email_body or not call_script) and len(text) > 100:
            paras = [p.strip() for p in text.split("\n\n") if p.strip()]
            if len(paras) >= 2:
                email_body = email_body or "\n\n".join(paras[:2])
                call_script = call_script or (paras[-1] if paras else text[:800])
        if not email_body or not call_script:
            return None, "could not parse response", None
        return {"emailBody": email_body, "callScript": call_script, "subject": subject}, None, None
    except Exception as e:
        import logging
        logging.warning("Gemini script generation failed: %s", e)
        err_msg = str(e).lower()
        detail = _sanitize_error_for_user(str(e))
        hint = "API error"
        if "quota" in err_msg or "rate" in err_msg or "429" in err_msg or "resource exhausted" in err_msg:
            hint = "rate limit (try again in a minute or check Gemini quota)"
        elif "blocked" in err_msg or "safety" in err_msg:
            hint = "content blocked"
        elif "api_key" in err_msg or "api key" in err_msg or "401" in err_msg or "403" in err_msg or "invalid" in err_msg and "key" in err_msg:
            hint = "invalid or missing API key (check GEMINI_API_KEY in backend/.env)"
        return None, hint, detail


def _library_script_for_topic(db: Session, topic: str) -> Optional[dict]:
    """Try to find a library script matching the topic (by issue_slug or title). Returns dict with emailBody, callScript, subject or None."""
    if not topic or not topic.strip():
        return None
    t = topic.strip().lower()
    # Normalize to slug-like: lowercase, replace spaces/slashes with hyphen
    slug_candidate = "".join(c if c.isalnum() or c == "-" else "-" for c in t)
    slug_candidate = "-".join(slug_candidate.split("-"))  # collapse multiple hyphens
    rows = db.query(ContactScript).filter(
        ContactScript.email_body.isnot(None),
        ContactScript.call_script.isnot(None),
    ).all()
    for row in rows:
        if not row.email_body or not row.call_script:
            continue
        if row.issue_slug and (row.issue_slug.lower() == t or row.issue_slug.lower() in t or slug_candidate and row.issue_slug.lower() in slug_candidate):
            return {"emailBody": row.email_body, "callScript": row.call_script, "subject": row.subject or "Constituent request"}
        if row.title and row.title.lower() in t:
            return {"emailBody": row.email_body, "callScript": row.call_script, "subject": row.subject or "Constituent request"}
    # Keyword map: common phrases -> issue_slug for lookup
    keywords_to_slug = {
        "climate": "climate", "healthcare": "healthcare", "voting": "voting-rights", "abortion": "abortion",
        "gun": "gun-violence", "immigration": "immigration", "economy": "economy-jobs", "inflation": "inflation",
        "student debt": "student-debt", "education": "education", "housing": "housing", "childcare": "childcare",
        "paid leave": "paid-leave", "minimum wage": "minimum-wage", "union": "unions", "infrastructure": "infrastructure",
        "drug price": "drug-pricing", "medicare": "medicare-social-security", "social security": "medicare-social-security",
        "lgbtq": "lgbtq-rights", "racial justice": "racial-justice", "criminal justice": "criminal-justice",
        "policing": "policing", "supreme court": "supreme-court", "democracy": "democracy-reform",
        "gerrymander": "gerrymandering", "campaign finance": "campaign-finance", "ukraine": "ukraine-nato",
        "china": "china", "border": "border-asylum", "daca": "daca", "dreamer": "daca", "tax": "tax-fairness",
        "debt ceiling": "deficit-debt", "opioid": "opioid", "mental health": "mental-health", "veteran": "veterans",
        "broadband": "broadband", "clean energy": "clean-energy", "environment": "environment",
        "women": "womens-rights", "equal pay": "womens-rights", "disability": "disability-rights",
        "elder": "elder-care", "snap": "snap", "food": "snap", "medicaid": "medicaid", "aca": "aca",
        "trade": "trade", "small business": "small-business", "agriculture": "agriculture", "farm": "agriculture",
        "tribal": "tribal", "native": "tribal", "postal": "postal-voting", "usps": "postal-voting",
        "net neutrality": "net-neutrality", "tech": "net-neutrality",
    }
    for keyword, slug in keywords_to_slug.items():
        if keyword in t:
            row = db.query(ContactScript).filter(ContactScript.issue_slug == slug).first()
            if row and row.email_body and row.call_script:
                return {"emailBody": row.email_body, "callScript": row.call_script, "subject": row.subject or "Constituent request"}
    return None


@app.post("/scripts/generate")
def script_generate(body: ScriptGenerateRequest, db: Session = Depends(get_db)):
    """Generate script: prefer library (50 topics), else placeholder. Gemini available but not used when library matches."""
    from config import GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY
    placeholder = {
        "emailBody": "I am a constituent and I'm writing to ask you to support [describe the issue]. Thank you.",
        "callScript": "Hi, I'm a constituent. I'm calling to ask you to support [describe the issue]. Thank you.",
        "subject": "Constituent request",
    }
    no_library_message = "No script in our library for this topic. Pick a topic above or add GEMINI_API_KEY for AI-generated scripts."

    # 1) When scriptId is provided: return library content if row has email_body and call_script
    if body.scriptId:
        row = db.query(ContactScript).filter(ContactScript.id == body.scriptId).first()
        if row and (row.email_body or "").strip() and (row.call_script or "").strip():
            return {
                "emailBody": row.email_body,
                "callScript": row.call_script,
                "subject": row.subject or "Constituent request",
            }

    topic = (body.issueText or body.issueTitle or "").strip()
    if not topic and body.issueOrBillId:
        topic = (body.issueOrBillId or "").strip()
    if not topic and body.scriptId:
        row = db.query(ContactScript).filter(ContactScript.id == body.scriptId).first()
        if row:
            topic = (row.title or row.issue_slug or row.bill_id or "").strip()

    # 2) Try to match topic to library (by slug or keywords)
    if topic:
        lib = _library_script_for_topic(db, topic)
        if lib:
            return lib

    # 3) No library match: return placeholder (demo: don't call Gemini to avoid rate limits)
    if not topic:
        return {**placeholder, "message": "Enter an issue or pick a topic above, then click Generate script."}
    return {**placeholder, "message": no_library_message}


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
