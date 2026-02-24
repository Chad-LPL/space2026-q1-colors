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
- **Contact form URLs:** When the Congress API does not provide an email or contact form URL, the backend fills in contact form links from [unitedstates/contact-congress](https://github.com/unitedstates/contact-congress) (by bioguide ID). The "Open email" / "Open contact form" actions in the contact modal use this when available.
- **District boundaries:** The map loads precomputed district paths from `frontend/public/districts_precomputed.json` (no backend required). To update district boundaries: run `python3 backend/scripts/fetch_districts_118.py` to fetch from Census (if needed), then `./scripts/refresh_districts.sh` from repo root. The refresh script copies the GeoJSON to the frontend and runs the precompute step so the map shows the latest boundaries without rendering artifacts.

- **Geocoding:** Census Geocoder (no key) for address → coordinates and district.

## Deploy on Render

Deploy so colleagues can use the app at a single link. **Repo:** [https://github.com/Chad-LPL/space2026-q1-colors](https://github.com/Chad-LPL/space2026-q1-colors).

You will create two things on Render: a **Web Service** (backend) and a **Static Site** (frontend). The frontend needs the backend URL so it can call the API.

### Backend build and run (for Render Web Service)

- **Root Directory:** `backend`
- **Build Command:** `python -m pip install -r requirements.txt` (DB is created at startup; build phase is read-only on Render.)
- **Start Command:** `python schema.py && python seed_scripts.py && uvicorn main:app --host 0.0.0.0 --port $PORT` (Render sets `$PORT`; do not change it.)
- **Environment variables:** `CONGRESS_API_KEY` (required), `GEMINI_API_KEY` (optional, for AI-generated scripts)

### Frontend build (for Render Static Site)

- **Root Directory:** `frontend`
- **Build Command:** `npm install && npm run build`
- **Publish Directory:** `dist`
- **Environment variable:** `VITE_API_BASE` = your backend URL (e.g. `https://congress-map-api.onrender.com`) with no trailing slash. Set this when creating the Static Site so the app can reach the API.

---

### Detailed manual steps (what you do on Render)

**Before you start**

- **Congress API key:** Get one at [api.data.gov/signup](https://api.data.gov/signup) (40-character string). Have it ready to paste.
- **Optional — Gemini API key:** For AI-generated contact scripts, get a key at [Google AI Studio](https://aistudio.google.com/app/apikey) and have it ready.
- **GitHub:** Make sure your latest code is pushed to [https://github.com/Chad-LPL/space2026-q1-colors](https://github.com/Chad-LPL/space2026-q1-colors).

---

**Part 1: Render account and connect GitHub**

1. In your browser, go to [https://render.com](https://render.com).
2. Click **Get Started for Free** or **Sign Up**.
3. Choose **Sign up with GitHub**. When asked, authorize Render to access your GitHub account.
4. After you sign in, you will see the Render **Dashboard**. If Render asks for a team or name, enter something simple (e.g. your name or "Congress Map").
5. To connect your repo:
   - Click **New +** (top right) and select **Web Service** (you will create the backend first).
   - Under "Connect a repository," search for **space2026-q1-colors** or **Chad-LPL/space2026-q1-colors**. Click **Connect** next to it.
   - If the repo does not appear: go to **Account Settings** (click your profile picture or name) → **GitHub** (or Integrations). Make sure Render has access to the **Chad-LPL/space2026-q1-colors** repository; grant access if prompted, then try connecting again.

---

**Part 2: Create and deploy the backend (Web Service)**

6. On the "Create a new Web Service" page, with your repo connected, fill in:
   - **Name:** e.g. `congress-map-api`. (This will be in the URL, e.g. `https://congress-map-api.onrender.com`.)
   - **Region:** Choose one near you (e.g. **Oregon (US West)**).
   - **Branch:** `main` (or whichever branch you use).
   - **Root Directory:** Click **Advanced**, then set **Root Directory** to: `backend`. (All build/start commands run from this folder.)
   - **Runtime:** **Python 3**.
   - **Build Command:** `python -m pip install -r requirements.txt`
   - **Start Command:** `python schema.py && python seed_scripts.py && uvicorn main:app --host 0.0.0.0 --port $PORT` (Render provides `$PORT`; do not change it.)
7. **Environment variables:**
   - Find the **Environment Variables** section (scroll or open **Advanced**).
   - Click **Add Environment Variable**.
   - **Key:** `CONGRESS_API_KEY`  
     **Value:** Paste your 40-character Congress API key. Leave **Secret** checked.
   - Optional: Click **Add Environment Variable** again. **Key:** `GEMINI_API_KEY` | **Value:** your Gemini API key. Save.
8. Under **Instance Type**, choose **Free** if you are on the free tier.
9. Click **Create Web Service**. Wait until the status shows **Live** (green). The first deploy may take a few minutes.
10. **Copy the backend URL:** At the top of the backend service page, you will see a URL like `https://congress-map-api.onrender.com`. Copy the full URL **without** a slash at the end. You will paste this into the frontend in Part 4.  
    **Quick test:** In a new tab, open `https://YOUR-BACKEND-URL/health` (replace with your URL). You should see something like `{"status":"ok"}`.

---

**Part 3: Create the frontend (Static Site)**

11. Back on the Render dashboard, click **New +** → **Static Site**.
12. Connect the **same** repository again: search for **space2026-q1-colors** or **Chad-LPL/space2026-q1-colors** and click **Connect**.
13. On "Create a new Static Site" fill in:
    - **Name:** e.g. `congress-map`. (Your app link will be like `https://congress-map.onrender.com`.)
    - **Branch:** `main` (or your branch).
    - **Root Directory:** Open **Advanced** and set to: `frontend`.
    - **Build Command:** `npm install && npm run build`
    - **Publish Directory:** `dist`. (Render serves the built files from this folder.)
14. **Environment variable (required):**
    - In **Environment Variables**, click **Add Environment Variable**.
    - **Key:** `VITE_API_BASE`  
      **Value:** Paste the backend URL you copied in step 10 (e.g. `https://congress-map-api.onrender.com`). No spaces; no slash at the end.
15. Click **Create Static Site**. Wait until the build completes and the site status is **Live**.

---

**Part 4: Get your app link and share it**

16. On the frontend service page, at the top you will see the **URL** (e.g. `https://congress-map.onrender.com`). This is the link your colleagues use.
17. Open that URL in your browser. Try the address search; if you see district and member data, the backend is connected.
18. Share this **frontend** URL with colleagues. Do not share the backend URL; they only need the frontend link.

---

**Later: updating the app or keys**

- **Code changes:** When you push to GitHub, Render will automatically rebuild and redeploy both services (if auto-deploy is enabled, which is the default).
- **Changing API keys or env vars:** Open the service (backend or frontend) on Render → **Environment** tab → edit the variable value → **Save Changes**. Render will redeploy that service.

---

## FEC integration (later)

FEC-related code is archived in `backend/archive_fec/` so we can later add fundraising totals per representative and donor insights. See that directory for the archived code and possible future integration.
