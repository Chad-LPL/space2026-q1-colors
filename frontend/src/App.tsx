import { Link } from "react-router-dom";
import CongressMap from "./CongressMap";

function App() {
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header
        style={{
          padding: "var(--space-3) var(--space-5)",
          borderBottom: "1px solid var(--color-border)",
          display: "flex",
          gap: "var(--space-4)",
          alignItems: "center",
          flexShrink: 0,
          background: "var(--color-surface)",
          boxShadow: "var(--shadow-sm)",
        }}
      >
        <Link to="/" style={{ fontWeight: "var(--font-bold)", fontSize: "var(--text-lg)", color: "var(--color-text)" }}>
          Congress Map
        </Link>
        <span style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)" }}>
          Find your district · Contact your Rep & Senators
        </span>
      </header>
      <main style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
        <CongressMap />
      </main>
    </div>
  );
}

export default App;
