"""Config for Congress Map backend: API keys, URLs, DB path."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from backend dir so the key is found when running from project root (e.g. uvicorn backend.main:app)
_backend_dir = Path(__file__).resolve().parent
load_dotenv(_backend_dir / ".env")

# Congress.gov API (api.data.gov key)
CONGRESS_API_KEY = os.getenv("CONGRESS_API_KEY", "")
CONGRESS_BASE_URL = "https://api.congress.gov/v3"

# Census Geocoder - no key required (onelineaddress accepts full address string)
CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"

# DB for cache, scripts, contact events
DB_PATH = Path(__file__).resolve().parent / "data" / "congress.db"
DATA_DIR = Path(__file__).resolve().parent / "data"

# Current Congress (119th). Member-by-district API may lag; we fall back to 118 in congress_client.
CURRENT_CONGRESS = 119
CONGRESS_FOR_MEMBER_LOOKUP = 118  # Use 118 for /member/congress/{congress}/{state}/{district} until 119 is populated

# Optional: LLM for AI-generated scripts (Gemini free tier: https://aistudio.google.com/app/apikey)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
