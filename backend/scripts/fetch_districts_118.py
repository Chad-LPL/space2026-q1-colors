#!/usr/bin/env python3
"""
Fetch 118th Congressional District boundaries from Census and save as GeoJSON.
Run from repo root: python backend/scripts/fetch_districts_118.py
Requires: pip install httpx pyshp
"""
import json
import zipfile
from io import BytesIO
from pathlib import Path

import httpx
import shapefile

# Census TIGER 2022: state-level 118th CD shapefiles (no national zip)
BASE_URL = "https://www2.census.gov/geo/tiger/TIGER2022/CD"
# All state FIPS (50 states + DC + PR)
STATE_FIPS = ["01", "02", "04", "05", "06", "08", "09", "10", "11", "12", "13", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "44", "45", "46", "47", "48", "49", "50", "51", "53", "54", "55", "56", "72"]
OUT_PATH = Path(__file__).resolve().parent.parent / "static" / "districts_118.geojson"


def _closed_ring(points_slice):
    """Return ring as list of [x,y], closed (first point repeated at end)."""
    ring = [[float(x), float(y)] for x, y in points_slice]
    if len(ring) >= 2 and ring[0] != ring[-1]:
        ring.append(ring[0][:])
    return ring


def _signed_area_ring(ring):
    """Shoelace formula. In lon/lat: CCW = positive, CW = negative.
    ESRI: exterior = CW (negative), interior/hole = CCW (positive)."""
    if len(ring) < 3:
        return 0.0
    n = len(ring)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += ring[i][0] * ring[j][1] - ring[j][0] * ring[i][1]
    return area * 0.5


def _point_in_polygon(pt, ring):
    """Ray-casting: True if pt is inside ring (ring is closed, exterior)."""
    x, y = pt
    n = len(ring)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _to_geojson_winding(ring, want_ccw):
    """Return ring in GeoJSON order: exterior should be CCW, holes CW."""
    area = _signed_area_ring(ring)
    is_ccw = area >= 0
    if want_ccw and not is_ccw:
        return list(reversed(ring))
    if not want_ccw and is_ccw:
        return list(reversed(ring))
    return ring


def shape_to_geojson_geom(shape):
    points = shape.points
    if not points:
        return None
    parts = getattr(shape, "parts", None) or [0]
    # Build closed rings and classify by signed area (ESRI: exterior CW = negative, hole CCW = positive)
    rings_with_area = []
    for j in range(len(parts)):
        start = parts[j]
        end = parts[j + 1] if j + 1 < len(parts) else len(points)
        ring = _closed_ring(points[start:end])
        if len(ring) < 4:  # need at least 3 distinct points + close
            continue
        area = _signed_area_ring(ring)
        rings_with_area.append((ring, area))
    if not rings_with_area:
        return None
    exteriors = [(r, a) for r, a in rings_with_area if a < 0]
    holes = [(r, a) for r, a in rings_with_area if a > 0]
    # If no ring has negative area (e.g. all stored CCW), treat all as separate exteriors (islands)
    if not exteriors:
        polygons = [_to_geojson_winding(r, want_ccw=True) for r, _ in rings_with_area]
        return {"type": "MultiPolygon", "coordinates": [[r] for r in polygons]}
    if not holes:
        holes = []
    # Single exterior: one Polygon with exterior + all holes (assign holes to this exterior)
    if len(exteriors) == 1:
        ext_ring, _ = exteriors[0]
        ext_ring = _to_geojson_winding(ext_ring, want_ccw=True)
        hole_rings = [_to_geojson_winding(r, want_ccw=False) for r, _ in holes]
        coords = [ext_ring] + hole_rings
        return {"type": "Polygon", "coordinates": coords}
    # Multiple exteriors (e.g. islands): assign each hole to the exterior that contains it
    polygons = []
    for ext_ring, _ in exteriors:
        ext_ring = _to_geojson_winding(ext_ring, want_ccw=True)
        its_holes = []
        for h_ring, _ in holes:
            # use first point of hole to decide containment
            if _point_in_polygon(h_ring[0], ext_ring):
                its_holes.append(_to_geojson_winding(h_ring, want_ccw=False))
        polygons.append([ext_ring] + its_holes)
    return {"type": "MultiPolygon", "coordinates": polygons}


def process_zip(z, all_features):
    shp_name = next((n for n in z.namelist() if n.endswith(".shp")), None)
    if not shp_name:
        return 0
    base = shp_name[:-4]
    with z.open(shp_name) as f:
        shp_buf = f.read()
    with z.open(base + ".shx") as f:
        shx_buf = f.read()
    with z.open(base + ".dbf") as f:
        dbf_buf = f.read()
    sf = shapefile.Reader(shp=BytesIO(shp_buf), shx=BytesIO(shx_buf), dbf=BytesIO(dbf_buf))
    fields = [f[0] for f in sf.fields[1:]]
    n = 0
    for i, shape in enumerate(sf.iterShapes()):
        rec = sf.record(i)
        props = dict(zip(fields, rec))
        statefp = str(props.get("STATEFP", "")).zfill(2)
        cd118 = props.get("CD118")
        if cd118 is not None:
            geoid = statefp + str(cd118).zfill(2)
        else:
            geoid = statefp + "00"
        props["GEOID"] = geoid
        if "STATEFP" not in props:
            props["STATEFP"] = statefp
        if "CD118" not in props:
            props["CD118"] = int(geoid[2:]) if len(geoid) >= 4 else 0
        geom = shape_to_geojson_geom(shape)
        if geom:
            all_features.append({"type": "Feature", "properties": props, "geometry": geom})
            n += 1
    return n


def main():
    out_path = OUT_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    all_features = []
    with httpx.Client(timeout=90, follow_redirects=True) as client:
        for statefp in STATE_FIPS:
            url = f"{BASE_URL}/tl_2022_{statefp}_cd118.zip"
            try:
                r = client.get(url)
                if r.status_code != 200:
                    print("Skip", statefp, r.status_code)
                    continue
                z = zipfile.ZipFile(BytesIO(r.content), "r")
                n = process_zip(z, all_features)
                print(statefp, n, "districts")
            except Exception as e:
                print("Error", statefp, e)
    geojson = {"type": "FeatureCollection", "features": all_features}
    with open(out_path, "w") as f:
        json.dump(geojson, f, separators=(",", ":"))
    print("Wrote", out_path, "with", len(all_features), "districts total")


if __name__ == "__main__":
    main()
