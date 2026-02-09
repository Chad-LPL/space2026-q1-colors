#!/usr/bin/env bash
# Copy district map data to frontend public and regenerate precomputed paths.
# Run from repo root. Requires backend/static/districts_118.geojson.
# To regenerate from Census first: python3 backend/scripts/fetch_districts_118.py
set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
if [[ ! -f backend/static/districts_118.geojson ]]; then
  echo "Missing backend/static/districts_118.geojson. Run: python3 backend/scripts/fetch_districts_118.py"
  exit 1
fi
echo "Copying districts GeoJSON to frontend public..."
cp backend/static/districts_118.geojson frontend/public/districts_118.geojson
echo "Precomputing district paths for the map..."
node frontend/scripts/precompute-districts.cjs
echo "Done. Reload the app to see updated districts."
