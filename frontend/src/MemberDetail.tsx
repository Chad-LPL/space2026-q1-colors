import { useState, useEffect } from "react";
import type { Member, MemberBill } from "./api";
import { getMemberBills, getMemberVotes } from "./api";

interface Props {
  member: Member;
  onClose: () => void;
  onContact: () => void;
  onContactAboutBill?: (member: Member, bill: MemberBill) => void;
}

export default function MemberDetail({ member, onClose, onContact, onContactAboutBill }: Props) {
  const [bills, setBills] = useState<MemberBill[]>([]);
  const [votes, setVotes] = useState<Array<{ position?: string; description?: string; date?: string; url?: string }>>([]);

  useEffect(() => {
    getMemberBills(member.id).then((r) => setBills(r.bills));
    getMemberVotes(member.id).then((r) => setVotes(r.votes));
  }, [member.id]);

  const partyLabel =
    member.party === "Republican" || member.party === "R"
      ? "Republican"
      : member.party === "Democratic" || member.party === "D"
        ? "Democratic"
        : member.party ?? "—";

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
          maxWidth: 520,
          width: "100%",
          maxHeight: "90vh",
          overflow: "auto",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ padding: "var(--space-5)", borderBottom: "1px solid var(--color-border)", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h2 style={{ margin: 0, fontSize: "var(--text-xl)", color: "var(--color-text)" }}>{member.name}</h2>
            <div style={{ color: "var(--color-text-secondary)", fontSize: "var(--text-sm)", marginTop: "var(--space-1)" }}>
              {partyLabel} · {member.state}
              {member.district != null && member.district > 0 ? `-${member.district}` : ""}
            </div>
            {member.phone && <div style={{ marginTop: "var(--space-2)" }}>📞 {member.phone}</div>}
            {(member.nextElection != null || member.firstElected != null) && (
              <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", marginTop: "var(--space-1)" }}>
                {member.nextElection != null && `Next election: ${member.nextElection}`}
                {member.nextElection != null && member.firstElected != null && " · "}
                {member.firstElected != null && `First elected: ${member.firstElected}`}
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              color: "var(--color-text-secondary)",
              fontSize: "1.5rem",
              cursor: "pointer",
              padding: 0,
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>

        <div style={{ padding: "var(--space-4) var(--space-5)" }}>
          {member.url && (
            <p style={{ margin: "0 0 var(--space-3)" }}>
              <a href={member.url} target="_blank" rel="noopener noreferrer">
                Official website →
              </a>
            </p>
          )}

          <div style={{ marginBottom: "var(--space-4)" }}>
            <button
              type="button"
              onClick={onContact}
              style={{
                padding: "var(--space-2) var(--space-4)",
                fontSize: "var(--text-base)",
                border: "none",
                borderRadius: "var(--radius-sm)",
                background: "var(--color-primary)",
                color: "var(--color-surface)",
                cursor: "pointer",
                fontWeight: "var(--font-semibold)",
              }}
            >
              Contact this member
            </button>
          </div>

          {bills.length > 0 && (
            <section style={{ marginBottom: "var(--space-5)" }}>
              <h3 style={{ fontSize: "var(--text-base)", marginBottom: "var(--space-2)", color: "var(--color-text-secondary)" }}>
                Sponsored legislation
              </h3>
              <ul style={{ margin: 0, paddingLeft: "var(--space-5)", fontSize: "var(--text-sm)" }}>
                {bills.slice(0, 10).map((b, i) => (
                  <li key={i} style={{ marginBottom: "var(--space-2)", listStyle: "none", marginLeft: "calc(-1 * var(--space-5))" }}>
                    <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "var(--space-2)" }}>
                      {b.url ? (
                        <a href={b.url} target="_blank" rel="noopener noreferrer">
                          {b.title || b.number || "Bill"}
                        </a>
                      ) : (
                        <span>{b.title || b.number || "Bill"}</span>
                      )}
                      {b.status && (
                        <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-secondary)" }}>{b.status}</span>
                      )}
                      {onContactAboutBill && (
                        <button
                          type="button"
                          onClick={() => onContactAboutBill(member, b)}
                          style={{
                            padding: "var(--space-1) var(--space-2)",
                            fontSize: "var(--text-xs)",
                            border: "1px solid var(--color-primary)",
                            borderRadius: "var(--radius-sm)",
                            background: "transparent",
                            color: "var(--color-primary)",
                            cursor: "pointer",
                          }}
                        >
                          Contact about this bill
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {votes.length > 0 && (
            <section>
              <h3 style={{ fontSize: "var(--text-base)", marginBottom: "var(--space-2)", color: "var(--color-text-secondary)" }}>
                Recent votes
              </h3>
              <ul style={{ margin: 0, paddingLeft: "var(--space-5)", fontSize: "var(--text-sm)" }}>
                {votes.slice(0, 8).map((v, i) => (
                  <li key={i} style={{ marginBottom: "var(--space-1)" }}>
                    <span style={{ color: v.position === "Yes" ? "var(--color-success)" : v.position === "No" ? "var(--color-error)" : "var(--color-text-secondary)" }}>
                      {v.position ?? "—"}
                    </span>
                    {v.description && ` · ${v.description.slice(0, 60)}${v.description.length > 60 ? "…" : ""}`}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {bills.length === 0 && votes.length === 0 && (
            <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
              Bill and vote data may still be loading or unavailable for this member.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
