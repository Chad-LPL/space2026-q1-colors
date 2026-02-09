/**
 * Precompute Great Lakes SVG path strings using the same projection as the map
 * (geoAlbersUsa, scale 1000, 800×600). Run from repo root:
 *   node frontend/scripts/precompute-great-lakes.cjs
 * Input: frontend/public/great-lakes.geojson
 * Output: frontend/public/great-lakes-paths.json
 */
const fs = require("fs");
const path = require("path");
const d3 = require("d3-geo");

const REPO_ROOT = path.resolve(__dirname, "../..");
const INPUT = path.join(REPO_ROOT, "frontend/public/great-lakes.geojson");
const OUTPUT = path.join(REPO_ROOT, "frontend/public/great-lakes-paths.json");

const WIDTH = 800;
const HEIGHT = 600;
const SCALE = 1000;

if (!fs.existsSync(INPUT)) {
  console.error("Input file not found:", INPUT);
  console.error("Create it by running the fetch script or ensure great-lakes.geojson exists.");
  process.exit(1);
}

const geojson = JSON.parse(fs.readFileSync(INPUT, "utf8"));
const features = geojson.features || [];

const projection = d3.geoAlbersUsa()
  .scale(SCALE)
  .translate([WIDTH / 2, HEIGHT / 2]);
const pathGenerator = d3.geoPath().projection(projection);

const outFeatures = [];
for (const f of features) {
  const pathD = pathGenerator(f);
  if (!pathD || pathD.length < 20) continue;
  const name = (f.properties && f.properties.name) || "Lake";
  outFeatures.push({ name, path: pathD });
}

const output = { width: WIDTH, height: HEIGHT, features: outFeatures };
fs.writeFileSync(OUTPUT, JSON.stringify(output), "utf8");
console.log("Wrote", outFeatures.length, "Great Lakes paths to", OUTPUT);
