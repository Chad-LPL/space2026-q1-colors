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
              padding: "var(--space-2) var(--space-3)",
              fontSize: "var(--text-base)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
              background: "var(--color-surface)",
              color: "var(--color-text)",
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
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                boxShadow: "var(--shadow-md)",
                zIndex: 10,
                maxHeight: 220,
                overflowY: "auto",
              }}
            >
              {suggestLoading && (
                <li style={{ padding: "var(--space-2) var(--space-3)", color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                  Finding addresses…
                </li>
              )}
              {!suggestLoading && suggestions.length === 0 && (
                <li style={{ padding: "var(--space-2) var(--space-3)", color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
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
                        padding: "var(--space-2) var(--space-3)",
                        textAlign: "left",
                        border: "none",
                        background: "transparent",
                        color: "var(--color-text)",
                        fontSize: "var(--text-base)",
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
            padding: "var(--space-2) var(--space-4)",
            fontSize: "var(--text-base)",
            fontWeight: "var(--font-semibold)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            background: "var(--color-primary)",
            color: "var(--color-surface)",
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Finding…" : "Find my district"}
        </button>
      </form>
      {error && (
        <span style={{ display: "block", marginTop: "var(--space-1)", color: "var(--color-error)", fontSize: "var(--text-sm)" }}>
          {error}
        </span>
      )}
    </div>
  );
}
