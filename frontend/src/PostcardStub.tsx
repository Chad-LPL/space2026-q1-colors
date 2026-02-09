interface Props {
  onClose: () => void;
}

export default function PostcardStub({ onClose }: Props) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "1rem",
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "#fff",
          border: "1px solid #e0e0e0",
          boxShadow: "0 8px 32px rgba(0,0,0,0.2)",
          borderRadius: 12,
          maxWidth: 400,
          width: "100%",
          padding: "1.5rem",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 style={{ margin: "0 0 0.75rem", fontSize: "1.25rem", color: "#1a1a1a" }}>📮 Send a postcard</h2>
        <p style={{ color: "#555", fontSize: "0.95rem", marginBottom: "1rem" }}>
          Soon you'll be able to pay for a postcard and postage and we'll mail it to your representative on your behalf. We're also exploring sending a postcard to another voter in your district about what matters to you.
        </p>
        <p style={{ color: "#555", fontSize: "0.85rem", marginBottom: "1rem" }}>
          Coming soon. In the meantime, use the contact options above to call or email.
        </p>
        <button
          type="button"
          onClick={onClose}
          style={{
            padding: "0.5rem 1rem",
            fontSize: "1rem",
            border: "none",
            borderRadius: 6,
            background: "#1976d2",
            color: "#fff",
            cursor: "pointer",
          }}
        >
          Got it
        </button>
      </div>
    </div>
  );
}
