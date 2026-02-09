import { useState, FormEvent, useEffect, useRef, useCallback } from "react";
import { geocodeSuggest } from "./api";

interface Props {
  onSubmit: (address: string) => Promise<string | null>;
}

const SUGGEST_DEBOUNCE_MS = 250;
const MIN_QUERY_LENGTH = 3;

export default function AddressSearch({ onSubmit }: Props) {
  const [address, setAddress] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<{ address: string }[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const q = address.trim();
    if (q.length < MIN_QUERY_LENGTH) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }
    const t = setTimeout(() => {
      setSuggestLoading(true);
      setShowSuggestions(true);
      geocodeSuggest(q, 5)
        .then((res) => {
          setSuggestions(res.suggestions || []);
        })
        .catch(() => setSuggestions([]))
        .finally(() => setSuggestLoading(false));
    }, SUGGEST_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [address]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      const trimmed = address.trim();
      if (!trimmed) return;
      setError(null);
      setShowSuggestions(false);
      setLoading(true);
      try {
        const err = await onSubmit(trimmed);
        setError(err);
      } finally {
        setLoading(false);
      }
    },
    [address, onSubmit]
  );

  const pickSuggestion = useCallback((s: string) => {
    setAddress(s);
    setShowSuggestions(false);
    setSuggestions([]);
  }, []);

  return (
    <div ref={wrapperRef} style={{ position: "relative", flex: 1, minWidth: 0 }}>
      <form
        onSubmit={handleSubmit}
        style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}
      >
        <div style={{ position: "relative", flex: "1", minWidth: 200 }}>
          <input
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
            placeholder="Enter your street address, city, state, ZIP"
            disabled={loading}
            autoComplete="off"
            style={{
              width: "100%",
              padding: "0.5rem 0.75rem",
              fontSize: "1rem",
              border: "1px solid #ccc",
              borderRadius: 6,
              background: "#fff",
              color: "#1a1a1a",
            }}
          />
          {showSuggestions && (
            <ul
              style={{
                position: "absolute",
                top: "100%",
                left: 0,
                right: 0,
                margin: 0,
                marginTop: 2,
                padding: "0.25rem 0",
                listStyle: "none",
                background: "#fff",
                border: "1px solid #ccc",
                borderRadius: 6,
                boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                zIndex: 10,
                maxHeight: 220,
                overflowY: "auto",
              }}
            >
              {suggestLoading && (
                <li style={{ padding: "0.5rem 0.75rem", color: "#555", fontSize: "0.9rem" }}>
                  Finding addresses…
                </li>
              )}
              {!suggestLoading && suggestions.length === 0 && (
                <li style={{ padding: "0.5rem 0.75rem", color: "#777", fontSize: "0.9rem" }}>
                  No suggestions. Add city and state for more suggestions.
                </li>
              )}
              {!suggestLoading &&
                suggestions.map((s, i) => (
                  <li key={i}>
                    <button
                      type="button"
                      onClick={() => pickSuggestion(s.address)}
                      style={{
                        width: "100%",
                        padding: "0.5rem 0.75rem",
                        textAlign: "left",
                        border: "none",
                        background: "transparent",
                        color: "#1a1a1a",
                        fontSize: "0.95rem",
                        cursor: "pointer",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = "#f0f0f0";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = "transparent";
                      }}
                    >
                      {s.address}
                    </button>
                  </li>
                ))}
            </ul>
          )}
        </div>
        <button
          type="submit"
          disabled={loading}
          style={{
            padding: "0.5rem 1rem",
            fontSize: "1rem",
            fontWeight: 600,
            border: "none",
            borderRadius: 6,
            background: "#1976d2",
            color: "#fff",
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Finding…" : "Find my district"}
        </button>
      </form>
      {error && (
        <span style={{ display: "block", marginTop: "0.25rem", color: "#c62828", fontSize: "0.9rem" }}>
          {error}
        </span>
      )}
    </div>
  );
}
