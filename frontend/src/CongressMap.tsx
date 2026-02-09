import { useState, useCallback, useEffect } from "react";
import { ComposableMap, Geographies, Geography, ZoomableGroup } from "react-simple-maps";
import {
  geocode,
  getMembers,
  type GeocodeResult,
  type MembersResponse,
  type Member,
} from "./api";
import AddressSearch from "./AddressSearch";
import MemberCards from "./MemberCards";
import MemberDetail from "./MemberDetail";
import ScriptFlow from "./ScriptFlow";
import PostcardStub from "./PostcardStub";

// US states TopoJSON – load so map is visible on first paint
const US_STATES_URL = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json";
const GREAT_LAKES_PATHS_URL = `${import.meta.env.BASE_URL}great-lakes-paths.json`.replace(/([^/])\/+/, "$1/");

// Precomputed district paths (same projection as map; clip rectangles stripped). Served from public/.
const DISTRICTS_PRECOMPUTED_URL = "/districts_precomputed.json";

/** True if path d is a full-viewport rectangle (clip artifact). Skip drawing these. */
function isViewportClipPath(d: string): boolean {
  const numbers = d.match(/-?[\d.]+/g);
  if (!numbers || numbers.length < 4) return false;
  const xs: number[] = [];
  const ys: number[] = [];
  for (let i = 0; i < numbers.length; i += 2) {
    xs.push(parseFloat(numbers[i]));
    if (i + 1 < numbers.length) ys.push(parseFloat(numbers[i + 1]));
  }
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const w = maxX - minX;
  const h = maxY - minY;
  return w > 850 && h > 450 && minX <= -60 && maxX >= 850 && minY <= 70 && maxY >= 530;
}

type PrecomputedDistrictFeature = { geoid: string; state: string; district: number; path: string };
type PrecomputedDistricts = { width: number; height: number; features: PrecomputedDistrictFeature[] };

type GreatLakesPaths = { width: number; height: number; features: Array<{ name: string; path: string }> };

export default function CongressMap() {
  const [geographyData, setGeographyData] = useState<unknown>(null);
  const [precomputedDistricts, setPrecomputedDistricts] = useState<PrecomputedDistricts | null>(null);
  const [precomputedLoading, setPrecomputedLoading] = useState(true);
  const [precomputedError, setPrecomputedError] = useState<string | null>(null);
  const [hoveredGeoid, setHoveredGeoid] = useState<string | null>(null);
  const [greatLakesPaths, setGreatLakesPaths] = useState<GreatLakesPaths | null>(null);
  const [geographyError, setGeographyError] = useState<string | null>(null);
  const [geocodeResult, setGeocodeResult] = useState<GeocodeResult | null>(null);
  const [membersData, setMembersData] = useState<MembersResponse | null>(null);
  const [membersError, setMembersError] = useState<string | null>(null);
  const [loadingMembers, setLoadingMembers] = useState(false);
  // Full US view on load: Albers USA center, zoom 1 so entire map is visible
  const [position, setPosition] = useState<{ coordinates: [number, number]; zoom: number }>({
    coordinates: [-96, 38],
    zoom: 1,
  });
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setMapReady(false);
    fetch(US_STATES_URL)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("Failed to load map"))))
      .then((data) => {
        if (!cancelled) {
          setGeographyData(data);
          setMapReady(true);
        }
      })
      .catch((err) => {
        if (!cancelled) setGeographyError(err?.message || "Could not load map");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Load precomputed Great Lakes paths (same projection as map) so lakes render as water gap.
  useEffect(() => {
    let cancelled = false;
    fetch(GREAT_LAKES_PATHS_URL)
      .then((r) => {
        if (!r.ok && import.meta.env.DEV) console.warn("Great Lakes paths not loaded:", r.status, GREAT_LAKES_PATHS_URL);
        return r.ok ? r.json() : null;
      })
      .then((data: GreatLakesPaths | null) => {
        if (!cancelled && data?.features?.length) setGreatLakesPaths(data);
      })
      .catch((err) => {
        if (import.meta.env.DEV) console.warn("Great Lakes fetch failed:", err);
      });
    return () => { cancelled = true; };
  }, []);

  // Load precomputed district paths from public/ (clip rectangles stripped; same projection as map).
  useEffect(() => {
    let cancelled = false;
    setPrecomputedLoading(true);
    setPrecomputedError(null);
    fetch(DISTRICTS_PRECOMPUTED_URL)
      .then((r) => (r.ok ? r.json() : null))
      .then((data: PrecomputedDistricts | null) => {
        if (!cancelled && data?.features?.length > 0) {
          setPrecomputedError(null);
          setPrecomputedDistricts(data);
        } else {
          if (!cancelled) setPrecomputedDistricts(null);
          if (!cancelled) setPrecomputedError("District boundaries could not be loaded. Click a state to see its members.");
        }
        if (!cancelled) setPrecomputedLoading(false);
      })
      .catch(() => {
        if (!cancelled) {
          setPrecomputedDistricts(null);
          setPrecomputedLoading(false);
          setPrecomputedError("District boundaries could not be loaded. Click a state to see its members.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);
  const [selectedMember, setSelectedMember] = useState<Member | null>(null);
  const [contactMember, setContactMember] = useState<Member | null>(null);
  const [showPostcard, setShowPostcard] = useState(false);

  const handleAddressSubmit = useCallback(async (address: string) => {
    const result = await geocode(address);
    if ("error" in result) {
      return result.error;
    }
    setGeocodeResult(result);
    setPosition({
      coordinates: [result.lng, result.lat],
      zoom: 6,
    });
    setMembersError(null);
    setLoadingMembers(true);
    try {
      const data = await getMembers(result.state, result.district);
      if ("error" in data) {
        setMembersError(data.error);
        setMembersData(null);
      } else {
        setMembersData(data);
      }
    } catch {
      setMembersError("Could not load members. Is the backend running?");
      setMembersData(null);
    } finally {
      setLoadingMembers(false);
    }
    return null;
  }, []);

  const fipsToAbbrev: Record<string, string> = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT",
    "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
    "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD", "25": "MA",
    "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV",
    "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD", "47": "TN",
    "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
    "56": "WY", "72": "PR",
  };

  // Load members for a specific state + district (used when clicking a district or state)
  const loadMembersForDistrict = useCallback((stateAbbrev: string, districtNum: number) => {
    if (!stateAbbrev || stateAbbrev.length !== 2) return;
    setMembersError(null);
    setLoadingMembers(true);
    getMembers(stateAbbrev, districtNum)
      .then((data) => {
        setLoadingMembers(false);
        if ("error" in data) {
          setMembersError(data.error);
          setMembersData(null);
        } else {
          setMembersData(data);
          setGeocodeResult({
            address: "",
            lat: 0,
            lng: 0,
            state: data.districtInfo.state,
            district: data.districtInfo.district,
            districtLabel: data.districtInfo.districtLabel,
            stateName: data.districtInfo.stateName,
            label: data.districtInfo.label,
          });
        }
      })
      .catch(() => {
        setLoadingMembers(false);
        setMembersError("Could not load members. Is the backend running?");
      });
  }, []);

  // Click state (state-level map): load district 1 as example
  const handleStateSelect = useCallback((stateFips: string) => {
    const abbrev = fipsToAbbrev[stateFips] || stateFips;
    if (!abbrev || abbrev.length !== 2) return;
    loadMembersForDistrict(abbrev, 1);
  }, [loadMembersForDistrict]);

  // Click district (district-level map): load that district’s members
  const handleDistrictSelect = useCallback((stateAbbrev: string, districtNum: number) => {
    if (!stateAbbrev || districtNum == null) return;
    loadMembersForDistrict(stateAbbrev, districtNum);
  }, [loadMembersForDistrict]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 60px)", gap: 0 }}>
      <div style={{ padding: "0.75rem 1rem", borderBottom: "1px solid #e0e0e0", flexShrink: 0, background: "#fff" }}>
        <AddressSearch onSubmit={handleAddressSubmit} />
        {geocodeResult && (
          <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "#555" }}>
            You're in <strong style={{ color: "#1a1a1a" }}>{geocodeResult.districtLabel}</strong> — {geocodeResult.label}
          </p>
        )}
      </div>

      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        <div style={{ flex: 1, position: "relative", minWidth: 0, minHeight: 400 }}>
          {!geographyData && !geographyError && (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", background: "#e8eef4", color: "#555", fontSize: "0.9rem" }}>
              Loading map…
            </div>
          )}
          {geographyError && (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", background: "#e8eef4", color: "#c62828", fontSize: "0.9rem" }}>
              {geographyError}
            </div>
          )}
          {geographyData && precomputedLoading && !precomputedDistricts && !precomputedError && (
            <div style={{ position: "absolute", bottom: 8, left: "50%", transform: "translateX(-50%)", padding: "0.35rem 0.75rem", background: "rgba(255,255,255,0.95)", border: "1px solid #ccc", borderRadius: 6, fontSize: "0.85rem", color: "#555", boxShadow: "0 2px 8px rgba(0,0,0,0.1)", zIndex: 10 }}>
              Loading district boundaries…
            </div>
          )}
          {geographyData && !precomputedLoading && precomputedError && (
            <div style={{ position: "absolute", bottom: 8, left: "50%", transform: "translateX(-50%)", padding: "0.35rem 0.75rem", background: "rgba(255,255,255,0.95)", border: "1px solid #f5a623", borderRadius: 6, fontSize: "0.85rem", color: "#333", boxShadow: "0 2px 8px rgba(0,0,0,0.1)", maxWidth: "90%" }}>
              {precomputedError}
            </div>
          )}
          <ComposableMap
            projection="geoAlbersUsa"
            projectionConfig={{ scale: 1000 }}
            width={800}
            height={600}
            style={{
              width: "100%",
              height: "100%",
              background: "#cfd8dc",
              minHeight: 400,
              visibility: geographyData ? "visible" : "hidden",
            }}
          >
            <ZoomableGroup
              center={position.coordinates}
              zoom={position.zoom}
              onMoveEnd={({ coordinates, zoom }: { coordinates: [number, number]; zoom: number }) =>
                setPosition({ coordinates, zoom })
              }
            >
              {geographyData && (
              <>
                {/* Mask: hide district fill where the Great Lakes are so lakes show through */}
                {precomputedDistricts && greatLakesPaths && (
                  <defs>
                    <mask id="districts-no-lakes-mask">
                      <rect x={-200} y={-100} width={1200} height={800} fill="white" />
                      {greatLakesPaths.features.map((lake) => (
                        <path key={`mask-${lake.name}`} d={lake.path} fill="black" />
                      ))}
                    </mask>
                  </defs>
                )}
                {/* When showing districts, draw states first so the full US is always visible */}
                {precomputedDistricts && (
                  <Geographies geography={geographyData}>
                    {({ geographies }: { geographies: Array<{ rsmKey: string; id?: string; properties?: Record<string, unknown> }> }) =>
                      geographies.map((geo: { rsmKey: string; id?: string; properties?: Record<string, unknown> }) => {
                        const rawId = geo.id ?? (geo.properties as { id?: string | number })?.id;
                        const fipsStr = rawId != null ? String(rawId).padStart(2, "0") : null;
                        return (
                          <Geography
                            key={`base-${geo.rsmKey}`}
                            geography={geo}
                            fill="#e8eaf6"
                            stroke="#455a64"
                            strokeWidth={0.75}
                            style={{ default: { outline: "none" }, hover: { fill: "#c5cae9", cursor: "pointer", outline: "none" }, pressed: { outline: "none" }}}
                            onClick={() => { if (fipsStr) handleStateSelect(fipsStr); }}
                          />
                        );
                      })
                    }
                  </Geographies>
                )}
                {precomputedDistricts ? (
                  <g
                    className="rsm-districts"
                    aria-label="Congressional districts"
                    mask={greatLakesPaths ? "url(#districts-no-lakes-mask)" : undefined}
                  >
                    {precomputedDistricts.features
                      .filter(
                        (f) =>
                          f.path &&
                          f.path.length >= 20 &&
                          !isViewportClipPath(f.path)
                      )
                      .map((f) => {
                        const isSelected =
                          geocodeResult != null &&
                          geocodeResult.state === f.state &&
                          geocodeResult.district === f.district;
                        const isHovered = hoveredGeoid === f.geoid;
                        return (
                          <path
                            key={f.geoid}
                            d={f.path}
                            fill={isSelected ? "#1565c0" : isHovered ? "#90a4ae" : "#78909c"}
                            stroke="#37474f"
                            strokeWidth={0.5}
                            style={{ outline: "none", cursor: "pointer" }}
                            onMouseEnter={() => setHoveredGeoid(f.geoid)}
                            onMouseLeave={() => setHoveredGeoid(null)}
                            onClick={() => handleDistrictSelect(f.state, f.district)}
                          />
                        );
                      })}
                  </g>
                ) : null}
                {!precomputedDistricts ? (
                  <Geographies geography={geographyData}>
                    {({ geographies }: { geographies: Array<{ rsmKey: string; id?: string; properties?: Record<string, unknown> }> }) =>
                      geographies.map((geo: { rsmKey: string; id?: string; properties?: Record<string, unknown> }) => {
                        const rawId = geo.id ?? (geo.properties as { id?: string | number })?.id;
                        const stateFips = rawId != null ? String(rawId).padStart(2, "0") : null;
                        const fipsToAbbrev: Record<string, string> = {
                          "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT",
                          "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
                          "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD", "25": "MA",
                          "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV",
                          "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
                          "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD", "47": "TN",
                          "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
                          "56": "WY", "72": "PR",
                        };
                        const abbrev = stateFips ? fipsToAbbrev[String(stateFips).padStart(2, "0")] : null;
                        const isSelected = geocodeResult && abbrev === geocodeResult.state;
                        return (
                          <Geography
                            key={geo.rsmKey}
                            geography={geo}
                            fill={isSelected ? "#1565c0" : "#78909c"}
                            stroke="#263238"
                            strokeWidth={1}
                            style={{
                              default: { outline: "none" },
                              hover: { fill: "#90a4ae", cursor: "pointer", outline: "none" },
                              pressed: { outline: "none" },
                            }}
                            onClick={() => {
                              if (stateFips) handleStateSelect(stateFips);
                            }}
                          />
                        );
                      })
                    }
                  </Geographies>
                ) : null}
                {/* Great Lakes: precomputed paths on top so there's a visible water gap between MI, WI, MN */}
                {greatLakesPaths && (
                  <g className="rsm-great-lakes" aria-hidden="true" style={{ pointerEvents: "none" }}>
                    {greatLakesPaths.features.map((lake, i) => (
                      <path
                        key={lake.name}
                        d={lake.path}
                        fill="#90caf9"
                        stroke="#42a5f5"
                        strokeWidth={0.6}
                        style={{ outline: "none" }}
                      />
                    ))}
                  </g>
                )}
              </>
              )}
            </ZoomableGroup>
          </ComposableMap>
        </div>

        <aside
          style={{
            width: 340,
            flexShrink: 0,
            borderLeft: "1px solid #e0e0e0",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            background: "#fff",
            boxShadow: "-2px 0 8px rgba(0,0,0,0.06)",
          }}
        >
          {membersError && (
            <div style={{ padding: "1rem", color: "#c62828" }}>{membersError}</div>
          )}
          {loadingMembers && (
            <div style={{ padding: "1rem", color: "#555" }}>Loading members…</div>
          )}
          {membersData && !loadingMembers && (
            <MemberCards
              districtInfo={membersData.districtInfo}
              representative={membersData.representative}
              senators={membersData.senators}
              membersError={membersData.membersError}
              onSelectMember={setSelectedMember}
              onContactMember={setContactMember}
              onSendPostcard={() => setShowPostcard(true)}
            />
          )}
          {!membersData && !loadingMembers && !membersError && (
            <div style={{ padding: "1rem", color: "#555", fontSize: "0.9rem" }}>
              Enter your address or click a district on the map to see your Representative and Senators.
            </div>
          )}
        </aside>
      </div>

      {selectedMember && (
        <MemberDetail
          member={selectedMember}
          onClose={() => setSelectedMember(null)}
          onContact={() => {
            setContactMember(selectedMember);
            setSelectedMember(null);
          }}
        />
      )}

      {contactMember && (
        <ScriptFlow
          member={contactMember}
          onClose={() => setContactMember(null)}
        />
      )}

      {showPostcard && (
        <PostcardStub onClose={() => setShowPostcard(false)} />
      )}
    </div>
  );
}
