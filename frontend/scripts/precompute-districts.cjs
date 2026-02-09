/**
 * Precompute district SVG path strings using the same projection as the map
 * (geoAlbersUsa, scale 1000, 800×600). Run from repo root:
 *   node frontend/scripts/precompute-districts.cjs
 * Input: backend/static/districts_118.geojson (or districts_119.geojson)
 * Output: frontend/public/districts_precomputed.json
 */
const fs = require("fs");
const path = require("path");
const d3 = require("d3-geo");

const REPO_ROOT = path.resolve(__dirname, "../..");
const DEFAULT_INPUT = path.join(REPO_ROOT, "backend/static/districts_118.geojson");
const OUTPUT = path.join(REPO_ROOT, "frontend/public/districts_precomputed.json");

const WIDTH = 800;
const HEIGHT = 600;
const SCALE = 1000;

// Census FIPS: 11=DC, 12=FL, 13=GA (was 11=FL, 12=GA — Georgia was missing)
const FIPS_TO_ABBREV = {
  "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT",
  "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
  "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD", "25": "MA",
  "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV",
  "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
  "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD", "47": "TN",
  "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
  "56": "WY", "72": "PR",
};

const inputPath = process.argv[2] ? path.resolve(process.cwd(), process.argv[2]) : DEFAULT_INPUT;

if (!fs.existsSync(inputPath)) {
  console.error("Input file not found:", inputPath);
  console.error("Usage: node frontend/scripts/precompute-districts.cjs [path/to/districts_118.geojson]");
  process.exit(1);
}

const geojson = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const features = geojson.features || [];

const projection = d3.geoAlbersUsa()
  .scale(SCALE)
  .translate([WIDTH / 2, HEIGHT / 2]);
const pathGenerator = d3.geoPath().projection(projection);

// d3-geo can add projection clip-extent and inset (AK/HI) rectangles; strip them so we don't draw grey boxes
function stripClipRect(pathStr) {
  if (!pathStr || typeof pathStr !== "string") return pathStr;
  // Exact strings (main view + insets) - remove ALL occurrences (replace only removes first)
  const exact = [
    "M-55,62L855,62L855,538L-55,538Z",
    "M-24.999999,420.000001L185.999999,420.000001L185.999999,533.999999L-24.999999,533.999999Z",
    "M186.000001,466.000001L284.999999,466.000001L284.999999,533.999999L186.000001,533.999999Z",
  ];
  let out = pathStr;
  for (const s of exact) {
    while (out.includes(s)) out = out.replace(s, "");
  }
  // Strip any axis-aligned rectangle subpath that matches main viewport or inset area
  const subpaths = out.split("Z").filter(Boolean);
  const kept = subpaths.filter((sub) => {
    const points = [];
    const re = /[ML](-?[\d.]+),(-?[\d.]+)/g;
    let m;
    while ((m = re.exec(sub))) points.push([parseFloat(m[1]), parseFloat(m[2])]);
    if (points.length !== 4 && points.length !== 5) return true;
    const xs = points.map((p) => p[0]);
    const ys = points.map((p) => p[1]);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const w = maxX - minX, h = maxY - minY;
    // Main viewport clip rect (covers whole map)
    const isMainViewport = w > 850 && h > 450 && minX <= -50 && maxX >= 850 && minY <= 60 && maxY >= 530;
    // AK/HI inset boxes
    const isInsetBox =
      w > 90 && h > 60 &&
      minX >= -35 && maxX <= 295 &&
      minY >= 415 && maxY <= 540;
    return !isMainViewport && !isInsetBox;
  });
  out = kept.join("Z") + (kept.length ? "Z" : "");
  return out.replace(/^Z/, "").replace(/\s*Z\s*Z/g, "Z").trim();
}

const outFeatures = [];
for (const f of features) {
  const props = f.properties || {};
  let stateFips = (props.STATEFP20 ?? props.STATEFP) != null ? String(props.STATEFP20 ?? props.STATEFP).padStart(2, "0") : null;
  if (stateFips === "00") stateFips = null;
  const cd = props.CD118FP ?? props.CD119FP ?? props.CD118 ?? props.CD119;
  const district = stateFips && cd != null ? parseInt(String(cd), 10) : 0;
  const geoid = (props.GEOID && props.GEOID !== "0000") ? props.GEOID : (props.GEOID20 ?? (stateFips && cd != null ? `${stateFips}${String(cd).padStart(2, "0")}` : null));
  const state = stateFips ? FIPS_TO_ABBREV[stateFips] || null : null;

  if (!state || stateFips === "00") continue;

  let pathD = pathGenerator(f);
  if (!pathD) continue;

  pathD = stripClipRect(pathD);
  if (!pathD || pathD.length < 20) continue;

  outFeatures.push({
    geoid: geoid || "",
    state: state || "",
    district,
    path: pathD,
  });
}

const publicDir = path.dirname(OUTPUT);
if (!fs.existsSync(publicDir)) {
  fs.mkdirSync(publicDir, { recursive: true });
}

const output = {
  width: WIDTH,
  height: HEIGHT,
  features: outFeatures,
};
fs.writeFileSync(OUTPUT, JSON.stringify(output), "utf8");
console.log("Wrote", outFeatures.length, "district paths to", OUTPUT);
