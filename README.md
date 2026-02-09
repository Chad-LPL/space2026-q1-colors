# Congress Map

Interactive US Congressional District map: find your district by address, see your Representative and Senators, view member details (bills, votes, contact), use pre-filled or AI-generated scripts to contact them, and track how many constituents have contacted each member about issues. Putting democracy into action.

## Quick start

Run both backend and frontend; address lookup and member data require the backend and `CONGRESS_API_KEY` (see API keys below).

1. **Backend (Python 3.9+)**
   ```bash
   cd backend
   python3 -m pip install -r requirements.txt
   cp .env.example .env   # then add your CONGRESS_API_KEY (see below)
   python3 schema.py
   python3 seed_scripts.py
   python3 -m uvicorn main:app --reload --host 127.0.0.1 --port 8001
   ```

2. **Frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Open http://localhost:5173. The Vite dev server proxies `/api` to the backend at port 8001.

## API keys

- **Congress.gov (required):** Get a free key at [api.data.gov/signup](https://api.data.gov/signup). Put it in `backend/.env` as:
  ```
  CONGRESS_API_KEY=your_40_character_key
  ```
  Do not commit `.env`; it is in `.gitignore`.

- **LLM (optional, for AI-generated contact scripts):** To have the app generate detailed email and call scripts from an issue or topic, set **GEMINI_API_KEY** in `backend/.env`. Without it, the contact script modal shows a placeholder and a message to add the key.
  - Get a free key at [Google AI Studio](https://aistudio.google.com/app/apikey), then add `GEMINI_API_KEY=your_key` to `backend/.env`.
  - OpenAI and Anthropic keys are also supported in config but Gemini is used first when set.

## Backend API (Congress Map)

- `GET /health` — Health check
- `GET /geocode?address=...` — Geocode address; returns state, district, lat/lng, districtLabel
- `GET /districts/geojson` — District boundaries (optional). Serves 119th (TIGER 2024) if `districts_119.geojson` exists, else 118th (TIGER 2022). Create with `fetch_districts_119.py` or `fetch_districts_118.py`, then `simplify_districts.py`. With that file, the map shows individual districts and clicking a district loads that district’s members.
- `GET /members?state=XX&district=N` — Representative + 2 Senators for that district
- `GET /members/{id}` — Member detail
- `GET /members/{id}/bills` — Sponsored legislation
- `GET /members/{id}/votes` — Recent votes
- `GET /scripts`, `GET /scripts/{id}` — Seed contact scripts
- `POST /scripts/generate` — Generate script (uses LLM if key set)
- `POST /contact-events` — Record a contact (for stats)
- `GET /contact-stats?memberId=...&issueId=...` — Weekly/monthly contact counts

## Project layout

- **backend/**  
  - `config.py` – Congress API key, Census Geocoder URL, DB path.  
  - `schema.py` – SQLite: contact_scripts, contact_events.  
  - `congress_client.py` – Congress.gov API v3 (members, bills, votes).  
  - `geocoder.py` – Census Geocoder (address → district; suggest for autocomplete).  
  - `main.py` – FastAPI app.  
  - `static/` – Optional `districts_119.geojson` or `districts_118.geojson` for district map boundaries (see Data sources).  
  - `archive_fec/` – Archived FEC/money-primary code for possible future fundraising integration.

- **frontend/**  
  - React + Vite + TypeScript, react-simple-maps.  
  - Congress Map: address search, US map (states), member cards (Rep + 2 Senators), member detail (bills, votes, official link, contact), script flow (generate/edit script, email/call, contact stats), stubbed "Send a postcard" modal.  
  - Old Money Primary / Story Finder components are in `frontend/src/archive/`.

## Data sources

- **Member data:** 119th Congress (Congress.gov API). The app requests current members for the 119th first and falls back to 118th when the API has no member for a given district yet.
- **District boundaries:** The map loads precomputed district paths from `frontend/public/districts_precomputed.json` (no backend required). To update district boundaries: run `python3 backend/scripts/fetch_districts_118.py` to fetch from Census (if needed), then `./scripts/refresh_districts.sh` from repo root. The refresh script copies the GeoJSON to the frontend and runs the precompute step so the map shows the latest boundaries without rendering artifacts.

- **Geocoding:** Census Geocoder (no key) for address → coordinates and district.

## FEC integration (later)

FEC-related code is archived in `backend/archive_fec/` so we can later add fundraising totals per representative and donor insights. See plan/docs for details.
