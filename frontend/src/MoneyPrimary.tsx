import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  CartesianGrid,
} from "recharts";

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

type TotalRow = {
  committee_id: string;
  candidate_id: string | null;
  committee_name: string | null;
  candidate_name: string | null;
  receipts: number;
};

export default function MoneyPrimary() {
  const [cycle, setCycle] = useState(2024);
  const [office, setOffice] = useState<string>("");
  const [selected, setSelected] = useState<{ committee_id: string; candidate_id: string | null } | null>(null);

  const { data: cyclesData } = useFetch<{ cycles: number[] }>(`${API_BASE}/cycles/available`);
  const cycles = cyclesData?.cycles?.length ? cyclesData.cycles : [2024, 2026];
  const hasNoData = !totalsLoading && totalsData?.totals?.length === 0;

  const totalsUrl = `${API_BASE}/totals?cycle=${cycle}&limit=20${office ? `&office=${office}` : ""}`;
  const { data: totalsData, loading: totalsLoading } = useFetch<{ totals: TotalRow[] }>(totalsUrl);

  const byMonthUrl =
    `${API_BASE}/receipts/by_month?cycle=${cycle}` +
    (selected?.committee_id ? `&committee_id=${encodeURIComponent(selected.committee_id)}` : "") +
    (selected?.candidate_id ? `&candidate_id=${encodeURIComponent(selected.candidate_id)}` : "");
  const { data: byMonthData } = useFetch<{ by_month: Array<{ year_month: string; total: number; small_donor_total: number; large_donor_total: number }> }>(byMonthUrl);

  const byStateUrl =
    `${API_BASE}/receipts/by_state?cycle=${cycle}` +
    (selected?.committee_id ? `&committee_id=${encodeURIComponent(selected.committee_id)}` : "") +
    (selected?.candidate_id ? `&candidate_id=${encodeURIComponent(selected.candidate_id)}` : "");
  const { data: byStateData } = useFetch<{ by_state: Array<{ state: string; total: number }> }>(byStateUrl);

  // Aggregate by month for chart (sum across committees)
  const byMonthAgg =
    byMonthData?.by_month?.reduce(
      (acc: Record<string, { year_month: string; total: number; small: number; large: number }>, row) => {
        const k = row.year_month;
        if (!acc[k]) acc[k] = { year_month: k, total: 0, small: 0, large: 0 };
        acc[k].total += row.total;
        acc[k].small += row.small_donor_total ?? 0;
        acc[k].large += row.large_donor_total ?? 0;
        return acc;
      },
      {}
    ) ?? {};
  const byMonthChart = Object.values(byMonthAgg).sort((a, b) => a.year_month.localeCompare(b.year_month));

  // Aggregate by state for chart
  const byStateAgg: Record<string, number> = {};
  byStateData?.by_state?.forEach((row) => {
    byStateAgg[row.state] = (byStateAgg[row.state] ?? 0) + row.total;
  });
  const byStateChart = Object.entries(byStateAgg)
    .map(([state, total]) => ({ state, total }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 15);

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Money Primary</h1>
      <p style={{ color: "#71767b", marginBottom: "1.5rem" }}>
        Who’s winning the money race? Totals over time, by state, and by donor size (small vs large).
      </p>

      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
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
        <label>
          Office:{" "}
          <select
            value={office}
            onChange={(e) => setOffice(e.target.value)}
            style={{ padding: "0.5rem", background: "#1a1f26", color: "#e7e9ea", border: "1px solid #2f3336", borderRadius: 4 }}
          >
            <option value="">All</option>
            <option value="P">President</option>
            <option value="H">House</option>
            <option value="S">Senate</option>
          </select>
        </label>
      </div>

      {hasNoData && (
        <div
          style={{
            padding: "1rem",
            marginBottom: "1.5rem",
            background: "#2a1f1f",
            border: "1px solid #4a3030",
            borderRadius: 8,
            color: "#e7e9ea",
          }}
        >
          No data for this cycle. Run ingest for this cycle or choose another (e.g. 2024).
        </div>
      )}

      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>Top committees by receipts</h2>
        <p style={{ color: "#71767b", fontSize: "0.875rem", marginBottom: "0.5rem" }}>
          Click a row to filter the charts below by that committee/candidate.{" "}
          {selected && (
            <button
              type="button"
              onClick={() => setSelected(null)}
              style={{
                padding: "0.25rem 0.5rem",
                background: "#2f3336",
                color: "#e7e9ea",
                border: "1px solid #3f4346",
                borderRadius: 4,
                cursor: "pointer",
              }}
            >
              Show all
            </button>
          )}
        </p>
        {totalsLoading && <p>Loading...</p>}
        {!totalsLoading && totalsData?.totals && totalsData.totals.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #2f3336", textAlign: "left" }}>
                  <th style={{ padding: "0.5rem" }}>Committee</th>
                  <th style={{ padding: "0.5rem" }}>Candidate</th>
                  <th style={{ padding: "0.5rem" }}>Receipts</th>
                </tr>
              </thead>
              <tbody>
                {totalsData.totals.map((t) => {
                  const isSelected =
                    selected?.committee_id === t.committee_id &&
                    (selected?.candidate_id ?? null) === (t.candidate_id ?? null);
                  return (
                    <tr
                      key={t.committee_id}
                      style={{
                        borderBottom: "1px solid #2f3336",
                        background: isSelected ? "#1d3a4a" : undefined,
                        cursor: "pointer",
                      }}
                      onClick={() =>
                        setSelected({
                          committee_id: t.committee_id,
                          candidate_id: t.candidate_id ?? null,
                        })
                      }
                    >
                      <td style={{ padding: "0.5rem" }} title={t.committee_id}>
                        {t.committee_name ?? t.committee_id}
                      </td>
                      <td style={{ padding: "0.5rem" }} title={t.candidate_id ?? undefined}>
                        {t.candidate_name ?? t.candidate_id ?? "—"}
                      </td>
                      <td style={{ padding: "0.5rem" }}>{formatMoney(t.receipts)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>Receipts over time (by month)</h2>
        {selected && (
          <p style={{ color: "#71767b", fontSize: "0.875rem", marginBottom: "0.5rem" }}>
            Filtered by selected committee/candidate.
          </p>
        )}
        {byMonthChart.length === 0 && <p style={{ color: "#71767b" }}>No monthly data for this cycle.</p>}
        {byMonthChart.length > 0 && (
          <div style={{ width: "100%", height: 300 }}>
            <ResponsiveContainer>
              <BarChart data={byMonthChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2f3336" />
                <XAxis dataKey="year_month" stroke="#71767b" />
                <YAxis stroke="#71767b" tickFormatter={(v) => formatMoney(v)} />
                <Tooltip formatter={(v: number) => formatMoney(v)} />
                <Legend />
                <Bar dataKey="small" name="Small donor (&lt;$200)" fill="#1d9bf0" stackId="a" />
                <Bar dataKey="large" name="Large donor ($200+)" fill="#7856ff" stackId="a" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      <section>
        <h2 style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>Receipts by state (top 15)</h2>
        {selected && (
          <p style={{ color: "#71767b", fontSize: "0.875rem", marginBottom: "0.5rem" }}>
            Filtered by selected committee/candidate.
          </p>
        )}
        {byStateChart.length === 0 && <p style={{ color: "#71767b" }}>No state data for this cycle.</p>}
        {byStateChart.length > 0 && (
          <div style={{ width: "100%", height: 300 }}>
            <ResponsiveContainer>
              <BarChart data={byStateChart} layout="vertical" margin={{ left: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2f3336" />
                <XAxis type="number" stroke="#71767b" tickFormatter={(v) => formatMoney(v)} />
                <YAxis type="category" dataKey="state" width={30} stroke="#71767b" />
                <Tooltip formatter={(v: number) => formatMoney(v)} />
                <Bar dataKey="total" name="Total" fill="#1d9bf0" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      <p style={{ marginTop: "2rem", fontSize: "0.875rem", color: "#71767b" }}>
        Data: FEC (Federal Election Commission). 2024 full cycle; 2026 in progress.
      </p>
    </div>
  );
}
