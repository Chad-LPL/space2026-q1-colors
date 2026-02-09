import { useEffect, useState } from "react";

const API_BASE = "/api";

function useFetch<T>(url: string | null): { data: T | null; loading: boolean; error: string | null } {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!url) {
      setLoading(false);
      return;
    }
    setLoading(true);
    fetch(url)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.statusText))))
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [url]);
  return { data, loading, error };
}

function formatMoney(n: number) {
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `$${(n / 1e3).toFixed(1)}K`;
  return `$${n.toFixed(0)}`;
}

export default function StoryFinder() {
  const [cycle, setCycle] = useState(2024);

  const { data: cyclesData } = useFetch<{ cycles: number[] }>(`${API_BASE}/cycles/available`);
  const cycles = cyclesData?.cycles?.length ? cyclesData.cycles : [2024, 2026];

  const storiesUrl = `${API_BASE}/stories?cycle=${cycle}`;
  const { data: storiesData, loading, error } = useFetch<{
    first_time_mega_donors: Array<{ contributor_name: string; contributor_zip: string; cycle_total: number; cycle: number; prior_cycle: number }>;
    double_givers: Array<{ contributor_name: string; contributor_zip: string; dem_total: number; rep_total: number; cycle: number }>;
    clusters_by_address: Array<{ contributor_zip: string; contributor_street_1: string; num_contributions: number; total: number; cycle: number }>;
    clusters_by_employer: Array<{ employer: string; num_contributions: number; total: number; cycle: number }>;
  }>(storiesUrl);

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Story Finder</h1>
      <p style={{ color: "#71767b", marginBottom: "1.5rem" }}>
        Surprising patterns in the data: first-time mega-donors, double givers (both sides), and address/employer clusters.
      </p>

      <div style={{ marginBottom: "1.5rem" }}>
        <label>
          Cycle:{" "}
          <select
            value={cycle}
            onChange={(e) => setCycle(Number(e.target.value))}
            style={{ padding: "0.5rem", background: "#1a1f26", color: "#e7e9ea", border: "1px solid #2f3336", borderRadius: 4 }}
          >
            {cycles.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading && <p>Loading stories...</p>}
      {error && <p style={{ color: "#f4212e" }}>{error}</p>}
      {!loading && !error && storiesData && (
        <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
          {!storiesData.first_time_mega_donors?.length &&
            !storiesData.double_givers?.length &&
            !storiesData.clusters_by_address?.length &&
            !storiesData.clusters_by_employer?.length && (
              <div
                style={{
                  padding: "1rem",
                  marginBottom: "1rem",
                  background: "#2a1f1f",
                  border: "1px solid #4a3030",
                  borderRadius: 8,
                  color: "#e7e9ea",
                }}
              >
                No story data for this cycle. Run ingest with Schedule A (do not use --skip-schedule-a) for this cycle, then run aggregates.
              </div>
            )}
          <section>
            <h2 style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>First-time mega-donors</h2>
            <p style={{ color: "#71767b", fontSize: "0.875rem", marginBottom: "0.5rem" }}>
              Contributors with large totals this cycle and minimal prior cycle activity.
            </p>
            {!storiesData.first_time_mega_donors?.length && <p>None found for this cycle.</p>}
            <div style={{ display: "grid", gap: "0.75rem" }}>
              {storiesData.first_time_mega_donors?.map((s, i) => (
                <div
                  key={i}
                  style={{
                    padding: "1rem",
                    background: "#1a1f26",
                    border: "1px solid #2f3336",
                    borderRadius: 8,
                  }}
                >
                  <strong>{s.contributor_name}</strong>
                  {s.contributor_zip && ` (${s.contributor_zip})`} — {formatMoney(s.cycle_total)} in {s.cycle} (prior cycle {s.prior_cycle}: minimal)
                </div>
              ))}
            </div>
          </section>

          <section>
            <h2 style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>Double givers</h2>
            <p style={{ color: "#71767b", fontSize: "0.875rem", marginBottom: "0.5rem" }}>
              Contributors who gave meaningful amounts to both Democratic and Republican committees.
            </p>
            {!storiesData.double_givers?.length && <p>None found for this cycle.</p>}
            <div style={{ display: "grid", gap: "0.75rem" }}>
              {storiesData.double_givers?.map((s, i) => (
                <div
                  key={i}
                  style={{
                    padding: "1rem",
                    background: "#1a1f26",
                    border: "1px solid #2f3336",
                    borderRadius: 8,
                  }}
                >
                  <strong>{s.contributor_name}</strong>
                  {s.contributor_zip && ` (${s.contributor_zip})`} — D: {formatMoney(s.dem_total)} / R: {formatMoney(s.rep_total)}
                </div>
              ))}
            </div>
          </section>

          <section>
            <h2 style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>Clusters by address</h2>
            <p style={{ color: "#71767b", fontSize: "0.875rem", marginBottom: "0.5rem" }}>
              Unusually high concentration of contributions from one address (zip + street).
            </p>
            {!storiesData.clusters_by_address?.length && <p>None found for this cycle.</p>}
            <div style={{ display: "grid", gap: "0.75rem" }}>
              {storiesData.clusters_by_address?.map((s, i) => (
                <div
                  key={i}
                  style={{
                    padding: "1rem",
                    background: "#1a1f26",
                    border: "1px solid #2f3336",
                    borderRadius: 8,
                  }}
                >
                  {s.contributor_street_1}, {s.contributor_zip} — {s.num_contributions} contributions, {formatMoney(s.total)}
                </div>
              ))}
            </div>
          </section>

          <section>
            <h2 style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>Clusters by employer</h2>
            <p style={{ color: "#71767b", fontSize: "0.875rem", marginBottom: "0.5rem" }}>
              Unusually high concentration of contributions from one employer.
            </p>
            {!storiesData.clusters_by_employer?.length && <p>None found for this cycle.</p>}
            <div style={{ display: "grid", gap: "0.75rem" }}>
              {storiesData.clusters_by_employer?.map((s, i) => (
                <div
                  key={i}
                  style={{
                    padding: "1rem",
                    background: "#1a1f26",
                    border: "1px solid #2f3336",
                    borderRadius: 8,
                  }}
                >
                  <strong>{s.employer}</strong> — {s.num_contributions} contributions, {formatMoney(s.total)}
                </div>
              ))}
            </div>
          </section>

          <p style={{ marginTop: "2rem", fontSize: "0.875rem", color: "#71767b" }}>
            Data: FEC (Federal Election Commission). Cycle selection applies to all story types.
          </p>
        </div>
      )}
    </div>
  );
}
