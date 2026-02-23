interface Props {
  onClose: () => void;
}

export default function PostcardStub({ onClose }: Props) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "var(--color-overlay)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "var(--space-4)",
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          boxShadow: "var(--shadow-lg)",
          borderRadius: "var(--radius-lg)",
          maxWidth: 400,
          width: "100%",
          padding: "var(--space-6)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 style={{ margin: "0 0 var(--space-3)", fontSize: "var(--text-xl)", color: "var(--color-text)" }}>📮 Send a postcard</h2>
        <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--text-base)", marginBottom: "var(--space-4)" }}>
          Soon you'll be able to pay for a postcard and postage and we'll mail it to your representative on your behalf. We're also exploring sending a postcard to another voter in your district about what matters to you.
        </p>
        <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--text-sm)", marginBottom: "var(--space-4)" }}>
          Coming soon. In the meantime, use the contact options above to call or email.
        </p>
        <button
          type="button"
          onClick={onClose}
          style={{
            padding: "var(--space-2) var(--space-4)",
            fontSize: "var(--text-base)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            background: "var(--color-primary)",
            color: "var(--color-surface)",
            cursor: "pointer",
          }}
        >
          Got it
        </button>
      </div>
    </div>
  );
}
