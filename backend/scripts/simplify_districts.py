#!/usr/bin/env python3
"""
Simplify districts GeoJSON by reducing polygon points so the file loads in the browser.
Run from repo root: python backend/scripts/simplify_districts.py [districts_118.geojson|districts_119.geojson]
Defaults to districts_118.geojson; pass districts_119.geojson to simplify 119th boundaries.
"""
import json
import sys
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"
DEFAULT_FILE = "districts_118.geojson"
IN_FILE = STATIC / (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FILE)
# Keep every Nth point (higher = smaller file, faster load). STEP=16 keeps file small and map responsive.
STEP = 16


def simplify_ring(ring):
    # Keep ring closed; need at least 4 points (3 vertices + closing point)
    if len(ring) <= 8:
        return ring
    out = []
    for i in range(0, len(ring) - 1, STEP):
        out.append(ring[i])
    out.append(ring[-1])  # closing point (same as ring[0] for closed ring)
    if len(out) < 4:
        return ring
    return out


def simplify_coords(coords):
    if not coords:
        return coords
    # Ring: list of [x, y]
    if isinstance(coords[0], (list, tuple)) and len(coords[0]) >= 2 and isinstance(coords[0][0], (int, float)):
        return simplify_ring(coords)
    # Polygon: list of rings; MultiPolygon: list of polygons
    return [simplify_coords(c) for c in coords]


def simplify_geometry(geom):
    if not geom or geom.get("type") not in ("Polygon", "MultiPolygon"):
        return geom
    geom = dict(geom)
    geom["coordinates"] = simplify_coords(geom["coordinates"])
    return geom


def normalize_properties(props):
    """Set GEOID, STATEFP, CD118 from *20/*118FP so consumers can use either naming."""
    if not props or not isinstance(props, dict):
        return
    if "GEOID20" in props and props["GEOID20"]:
        props["GEOID"] = props["GEOID20"]
    if "STATEFP20" in props and props["STATEFP20"] is not None:
        props["STATEFP"] = props["STATEFP20"]
    cd = props.get("CD118FP") or props.get("CD119FP")
    if cd is not None:
        try:
            props["CD118"] = int(cd) if str(cd).isdigit() else 0
        except (TypeError, ValueError):
            props["CD118"] = 0


def main():
    with open(IN_FILE) as f:
        data = json.load(f)
    features = data.get("features") or []
    for f in features:
        if f.get("geometry"):
            f["geometry"] = simplify_geometry(f["geometry"])
        normalize_properties(f.get("properties"))
    with open(IN_FILE, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print("Simplified", len(features), "districts in", IN_FILE)


if __name__ == "__main__":
    main()
