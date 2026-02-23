# Demo Day Presentation – Congress Map

**Format:** Slides for intro / challenges / build / next, then live demo.  
**Time:** ~10 minutes (aim for ~5 min talk, ~4–5 min demo, buffer for Q&A).

Use this as your slide outline and script. Fill in any remaining blanks as you rehearse.

---

## 1. Introducing the project

### What problem are we solving?

- Many people don’t know who represents them or how to contact Congress in a way that actually gets counted.
- Friction: finding your district, your Rep and Senators, what to say, and where to send it (forms vs email, staff expectations).

### What we’re building

- **Congress Map**: one place to find your district by address, see your Representative and two Senators, and take action.
- **Core flow:** Address → district on map → member cards (Rep + 2 Senators) → member detail (bills, votes) → **contact flow**: pick or generate a script (email/call), open contact form or copy text, record that you contacted (for stats).
- **Differentiators:** Scripts designed for impact (research-backed: clear ask, constituent ID, one issue, short); optional AI-generated scripts (Gemini); contact stats (last 7/30 days) so users see others are contacting too.

### What am I trying to learn

- **Problem-solving in a domain I care about** – civic engagement and “contact your rep” in one place.
- **Development process in Cursor** – to strengthen my work as a Product Manager and our **Nova** (AI-native) approach to building software.

---

## 2. Challenges (technical and logistical)

### Technical

- **Congress.gov API:** API key, rate limits, varying response shape. We use in-memory caching (long TTL for bios, shorter for votes/bills) and 119th/118th fallback when a district isn’t in the current Congress yet.
- **District boundaries (biggest challenge):** GeoJSON from Census had to be fetched, simplified, and precomputed for the frontend so the map renders cleanly. Pipeline: `fetch_districts_118.py` / `fetch_districts_119.py` → `simplify_districts.py` → frontend `precompute-districts.cjs` → `districts_precomputed.json`. Getting boundaries performant and artifact-free took real iteration.
- **Contact form URLs:** Congress API often doesn’t provide them. We fill gaps with [unitedstates/contact-congress](https://github.com/unitedstates/contact-congress) and [congress-legislators](https://github.com/unitedstates/congress-legislators), with validation so we only use congressional domains.
- **Optional LLM:** Script generation with Gemini; app works without it via a curated script library (50 topics).

### Logistical

- **Multiple data sources:** Congress.gov, Census, unitedstates repos – keeping member IDs (bioguide) and contact URLs consistent across them.
- **Data freshness:** 119th rollout and district boundary updates; caching and fallbacks keep the app usable.

---

## 3. How we built it and overcame challenges

### Stack

- **Backend:** FastAPI, SQLite (contact_scripts, contact_events), Congress.gov client with caching, Census Geocoder, optional Gemini.
- **Frontend:** React + Vite + TypeScript, react-simple-maps; flow: AddressSearch → CongressMap → MemberCards → MemberDetail → ScriptFlow (scripts, generate, email/call, record contact, stats).

### Design decisions

- **Script library first:** 50 seed scripts so the app is useful without an LLM key; messaging follows staffer research (constituent ID, one ask, short, polite).
- **Contact events:** POST when user records “I emailed/called”; stats per member (and optional issue) for “X people contacted in the last 7/30 days.”
- **Graceful degradation:** No Gemini → library + placeholder; no district GeoJSON → state-level map; missing contact URL → show what’s available.

### Overcoming the district-boundary challenge

- Clear pipeline: fetch from Census → simplify (reduce complexity for the client) → precompute paths for the map library so we don’t render raw GeoJSON at runtime.
- Documented in README and scripts so boundaries can be refreshed when Census or Congress updates.

---

## 4. Demo the app (~4–5 min)

### Flashy version: real call + contact form

Do both during the demo so the audience sees the full loop: **call a member’s office**, then **submit their contact form** with the same issue. Very memorable.

**Flow (keep tight for time):**

1. **Address** – Type a real address; show district and members (30 sec).
2. **Pick one member** – e.g. your Rep. Open Contact → choose one script (e.g. “Support climate action”). Show the call script and email body (30 sec).
3. **Call** – Click “Call” / dial the number (from the app or member detail). Put phone on speaker briefly. Say something like: “Hi, I’m a constituent from [city]. I’m calling to ask the Representative to support strong climate legislation. You can just record my position. Thank you.” Hang up. (1–1.5 min max.)
4. **Contact form** – “Open contact form & copy message.” Paste the email body, add name/address in the form, submit. Show the confirmation if possible (1–1.5 min).
5. **Record in app** – Mark “I emailed” and “I called” in the app so stats update. Point out “X contacted in the last 7 days” (30 sec).

**Prep so it’s smooth:**

- **Phone:** Use an address in a district where the Rep’s office number is in the app and you’re comfortable calling. Have your phone unlocked and volume up; consider speaker so the room can hear you say the one line.
- **Backup if no one answers:** Congressional offices often go to voicemail. Plan A: leave a short voicemail with the same script. Plan B: “They’re not picking up—here’s what you’d say,” then read the script and move to the contact form. Either way you still demo the call UI and the script.
- **Contact form:** Pick a member whose contact form URL we have (Congress API or contact-congress). Test once beforehand so you know the form loads and you can paste + submit quickly. Have a throwaway or short message so you’re not spamming a real office if you prefer.
- **Timing:** If you’re strict on 10 min, do either call *or* form live and narrate the other (“I’d do the same for email…”). Otherwise do both and trim a slide or two.

### Prep (general)

- Backend + frontend running; `CONGRESS_API_KEY` in `backend/.env`. Optional: `GEMINI_API_KEY` for AI script generation.
- Use an address that geocodes reliably and that matches a member with a working phone number and contact form.
- If showing the map, ensure district boundaries are built (see README: `refresh_districts.sh` / precomputed paths).

---

## 5. What’s next and what I learned

### What’s next

- **Postcard:** Turn the stubbed Postcard flow into a real flow (e.g. print-ready or mail service).
- **Polish:** Ship-ready polish – mobile, accessibility, copy, and any UX tweaks from testing.

### What I learned

- **Integrating APIs and combining data sources** – Congress.gov, Census Geocoder, and unitedstates repos; getting API keys and wiring them into the solution.
- **PM + Cursor/Nova** – How to drive an AI-native development process and problem-solve in a domain I care about.

---

## Slide design: levity & fun

Keep the content solid but the *vibe* light so it doesn’t feel like a dry product pitch. Ideas:

**Tone**

- One short joke or relatable line per section (e.g. challenges: “District boundaries: the map tried to render 435 districts at once. It did not go well.”).
- Self-deprecation works: “I learned that Congress’s API returns members in three different keys. Why? Nobody knows.”
- One slide can be purely fun (e.g. “Demo” = “Time to actually call Congress. What could go wrong?”).

**Visuals**

- **Memes or simple illustrations:** A “me vs. the district boundary GeoJSON” style image, or a “finding your rep without this app” (many browser tabs) vs “with this app” (one screen).
- **Screenshots with callouts:** Annotate the UI with labels like “This is where the magic happens” or “50 scripts, zero judgment.”
- **Minimal text, big type:** One phrase per slide with a single idea (e.g. “One address. One map. Your three members.”).
- **Consistent gag:** e.g. a small mascot or recurring visual (map pin, capitol building) that appears in a funny way on each slide.

**Copy ideas (drop-in or adapt)**

- Title: “Congress Map: Your reps. Your script. Your move.” or “Find your district. Contact your rep. No PhD required.”
- Problem: “Nobody knows who represents them. And ‘just Google it’ is … not great.”
- What we built: “Address in → district + Rep + 2 Senators → one click to call or email. With a script so you don’t stare at a blank form.”
- Challenges: “District boundaries: we made the map. The map did not make it easy.” / “Congress’s API: sometimes the members are under ‘members.’ Sometimes under ‘results.’ Sometimes under ‘data.’ We check all three.”
- Demo: “Live demo: I’m going to call my Rep. Yes, really.” / “Next: I’m submitting their contact form. In front of you. No take-backs.”
- What’s next: “Postcards. Because email is great but paper is *chef’s kiss*.” / “Polish. So it doesn’t look like I built it in a weekend. (I did. But still.)”

**What to avoid**

- Don’t sacrifice clarity for jokes—if a slide is funny but vague, add one clear takeaway line.
- Keep partisan stuff out of the room; the app is about *contacting* Congress, not which side you’re on.
- One or two laugh lines per section is enough; too many and it feels like stand-up instead of a demo.

---

## Slide outline (for ~10 min)

| Slide | Content | Vibe idea |
|-------|--------|-----------|
| 1 | Title: Congress Map – Find your district, contact your Rep & Senators | Subtitle or one-liner for levity (e.g. “No PhD required”) |
| 2 | Problem: people don’t know who represents them or how to contact in a way that counts | One relatable line (e.g. “Just Google it” is not a strategy) |
| 3 | What we built: one flow – address → district → members → detail → contact | Big simple diagram or “One address. Three members. One script.” |
| 4 | What I’m trying to learn: problem-solving in civic tech + Cursor / Nova | Keep short; PM + AI-native angle |
| 5 | Challenges: Congress API, **district boundaries** (biggest), contact URLs, optional LLM | One joke (e.g. map + 435 districts = pain) |
| 6 | How we built it: FastAPI + React, script library + research, graceful degradation | Screenshot or tiny architecture doodle |
| 7 | What’s next: postcard flow, polish to ship | Fun line (postcards = chef’s kiss, etc.) |
| 8 | What I learned: APIs + data sources, PM in an AI-native workflow | One concrete takeaway |
| 9 | **Demo** – “I’m calling my Rep and submitting their form. Live.” | Build anticipation; keep slide minimal |
| 10 | Thanks / Q&A | Clean and friendly |

---

## Appendix: Tech deep dive (for devs / appendix slide)

Use this for an appendix slide or handout for technical audiences.

### Backend

- **Runtime:** Python 3.9+, FastAPI, Uvicorn. Run: `uvicorn main:app --reload --host 127.0.0.1 --port 8001`.
- **Config** ([`backend/config.py`](backend/config.py)): `.env` in backend dir. `CONGRESS_API_KEY` (required, api.data.gov). `GEMINI_API_KEY` (optional). `CENSUS_GEOCODER_URL` (no key). `DB_PATH` = `backend/data/congress.db`. `CURRENT_CONGRESS` = 119; `CONGRESS_FOR_MEMBER_LOOKUP` = 118 for member-by-district until 119 is fully populated.
- **Database:** SQLite via SQLAlchemy 2. Two tables: `contact_scripts` (id, title, body, subject, bill_id, issue_slug, email_body, call_script) and `contact_events` (id, member_id, issue_id, topic, contact_type, created_at). No PII. Schema in [`backend/schema.py`](backend/schema.py). Seed scripts: `python seed_scripts.py` (loads 50 topics from `script_library.py`).
- **Congress.gov client** ([`backend/congress_client.py`](backend/congress_client.py)): Congress.gov API v3, base `https://api.congress.gov/v3`. In-memory cache: key → (expires_at, data). TTL 7 days for member/bio, 1 hour for votes/bills. Handles varying response shapes (`members` / `results` / `data`). Member lookup: House by state+district (`/member/congress/{congress}/{state}/{district}?currentMember=true`), Senators from member list; tries 119th then 118th. Contact URLs: from API when present; else [`contact_congress.py`](backend/contact_congress.py) (unitedstates/contact-congress by bioguide) and [`legislators_current.py`](backend/legislators_current.py) (congress-legislators). Validation in [`contact_validation.py`](backend/contact_validation.py) (congressional domains only).
- **Geocoder** ([`backend/geocoder.py`](backend/geocoder.py)): Census Geocoder `geographies/onelineaddress`, no key. Params: address, benchmark `Public_AR_Current`, vintage `Current_Current`, layers `118th Congressional Districts`. Returns state (FIPS → 2-letter), district number, lat/lng, districtLabel. `geocode_suggest()` for typeahead (up to N address suggestions).
- **API surface** ([`backend/main.py`](backend/main.py)): `GET /health`, `GET /geocode`, `GET /geocode/suggest`, `GET /members?state=&district=`, `GET /members/{id}`, `GET /members/{id}/bills`, `GET /members/{id}/votes`, `GET /scripts`, `GET /scripts/{id}`, `POST /scripts/generate`, `POST /contact-events`, `GET /contact-stats?memberId=&issueId=&topic=`, `GET /districts/geojson` (optional). Debug: `GET /debug/congress-api`, `GET /debug/gemini`. CORS allows all origins.
- **Script generation:** `POST /scripts/generate`: (1) If `scriptId` provided, return that row’s email_body/call_script/subject. (2) Else derive topic from request; match to library by `issue_slug` or keyword map. (3) If no match, return placeholder (no PII). Gemini integration is implemented (`_generate_script_gemini` in main.py, `gemini-2.0-flash`) but not currently invoked from the endpoint; design is library-first, optional LLM later.
- **Contact stats:** `GET /contact-stats` filters `ContactEvent` by member_id, optional issueId/topic, then counts `created_at >= week_ago` and `>= month_ago` for last7Days and last30Days.

### Frontend

- **Stack:** React 18, Vite 5, TypeScript. No global state library; state lives in [`CongressMap.tsx`](frontend/src/CongressMap.tsx) and children. Map: [`react-simple-maps`](https://www.npmjs.com/package/react-simple-maps) (ComposableMap, Geographies, Geography, ZoomableGroup), projection `geoAlbersUsa`. Dev: `npm run dev` (Vite dev server); proxy `/api` → `http://127.0.0.1:8001` (rewrite strips `/api`).
- **Data flow:** Single parent [`CongressMap`](frontend/src/CongressMap.tsx) holds: geographyData (US states TopoJSON from CDN), precomputedDistricts (from `/districts_precomputed.json` in public), geocodeResult, membersData, selectedMember, contactMember, position (map center/zoom). [`AddressSearch`](frontend/src/AddressSearch.tsx) calls `geocode()` on submit → CongressMap sets geocodeResult, position, then `getMembers(state, district)` → sets membersData. Map click (state or district) → `loadMembersForDistrict(state, district)` → same members fetch + synthetic geocodeResult. Member card click → setSelectedMember (MemberDetail); “Contact” → setContactMember (ScriptFlow). ScriptFlow fetches scripts, generate, contact-stats, member bills; records contact via `recordContactEvent()`.
- **API layer** ([`frontend/src/api.ts`](frontend/src/api.ts)): All requests to `/api/*` (proxied to backend). Geocode cache: in-memory Map, max 50 entries, 30 min TTL. Types: GeocodeResult, Member, MembersResponse, ContactStats, ScriptItem, ScriptDetail, ScriptGenerateResponse, etc. Errors normalized (e.g. backend unreachable, Congress key missing).
- **Key components:**  
  - **AddressSearch:** typeahead via `geocodeSuggest()`; submit calls parent `onSubmit(address)`.  
  - **CongressMap:** loads US states + Great Lakes paths + precomputed districts; highlights district by geoid; handles state/district click; renders MemberCards, MemberDetail, ScriptFlow, PostcardStub.  
  - **MemberCards:** rep + 2 senators; “Contact” / “Send postcard” open ScriptFlow / PostcardStub.  
  - **MemberDetail:** member bio, bills (getMemberBills), votes (getMemberVotes), links, “Contact” opens ScriptFlow.  
  - **ScriptFlow:** script list (getScripts), pick or custom issue, generate (getScript or generateScript), email/call copy + “Open contact form”, recordContactEvent, getContactStats (last 7/30 days).
- **District boundaries:** Map does not fetch backend GeoJSON at runtime. It uses precomputed paths: `frontend/public/districts_precomputed.json` (generated by `frontend/scripts/precompute-districts.cjs` from GeoJSON). Backend can serve raw GeoJSON from `backend/static/districts_118.geojson` or `districts_119.geojson` for other clients; pipeline: `backend/scripts/fetch_districts_118.py` (or 119) → `simplify_districts.py` → copy to frontend → precompute. Viewport-clip rectangles in path data are detected and not drawn (`isViewportClipPath()`).

### One-liner for the slide

**Backend:** FastAPI + SQLite (scripts, contact events). Congress.gov v3 client (cached, 119/118 fallback). Census Geocoder (no key). Optional Gemini for script generation; library-first.  
**Frontend:** React + Vite + TS, react-simple-maps. Single parent (CongressMap) state; flow: AddressSearch → geocode → getMembers → MemberCards → MemberDetail / ScriptFlow (scripts, generate, record contact, stats). Precomputed district paths from public/.
