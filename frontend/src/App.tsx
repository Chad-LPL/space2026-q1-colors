import { Link } from "react-router-dom";
import CongressMap from "./CongressMap";

function App() {
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header
        style={{
          padding: "0.75rem 1.25rem",
          borderBottom: "1px solid #e0e0e0",
          display: "flex",
          gap: "1rem",
          alignItems: "center",
          flexShrink: 0,
          background: "#fff",
          boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
        }}
      >
        <Link to="/" style={{ fontWeight: 700, fontSize: "1.2rem", color: "#1a1a1a" }}>
          Congress Map
        </Link>
        <span style={{ fontSize: "0.9rem", color: "#555" }}>
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
