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
          maxWidth: 520,
          width: "100%",
          maxHeight: "90vh",
          overflow: "auto",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ padding: "1.25rem", borderBottom: "1px solid #e0e0e0", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h2 style={{ margin: 0, fontSize: "1.25rem", color: "#1a1a1a" }}>{member.name}</h2>
            <div style={{ color: "#555", fontSize: "0.9rem", marginTop: 4 }}>
              {partyLabel} · {member.state}
              {member.district != null && member.district > 0 ? `-${member.district}` : ""}
            </div>
            {member.phone && <div style={{ marginTop: 6 }}>📞 {member.phone}</div>}
            {(member.nextElection != null || member.firstElected != null) && (
              <div style={{ fontSize: "0.85rem", color: "#555", marginTop: 4 }}>
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
              color: "#555",
              fontSize: "1.5rem",
              cursor: "pointer",
              padding: 0,
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>

        <div style={{ padding: "1rem 1.25rem" }}>
          {member.url && (
            <p style={{ margin: "0 0 0.75rem" }}>
              <a href={member.url} target="_blank" rel="noopener noreferrer">
                Official website →
              </a>
            </p>
          )}

          <div style={{ marginBottom: "1rem" }}>
            <button
              type="button"
              onClick={onContact}
              style={{
                padding: "0.5rem 1rem",
                fontSize: "1rem",
                border: "none",
                borderRadius: 6,
                background: "#1976d2",
                color: "#fff",
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              Contact this member
            </button>
          </div>

          {bills.length > 0 && (
            <section style={{ marginBottom: "1.25rem" }}>
              <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem", color: "#555" }}>
                Sponsored legislation
              </h3>
              <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.9rem" }}>
                {bills.slice(0, 10).map((b, i) => (
                  <li key={i} style={{ marginBottom: 8, listStyle: "none", marginLeft: "-1.25rem" }}>
                    <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "0.5rem" }}>
                      {b.url ? (
                        <a href={b.url} target="_blank" rel="noopener noreferrer">
                          {b.title || b.number || "Bill"}
                        </a>
                      ) : (
                        <span>{b.title || b.number || "Bill"}</span>
                      )}
                      {b.status && (
                        <span style={{ fontSize: "0.8rem", color: "#555" }}>{b.status}</span>
                      )}
                      {onContactAboutBill && (
                        <button
                          type="button"
                          onClick={() => onContactAboutBill(member, b)}
                          style={{
                            padding: "0.25rem 0.5rem",
                            fontSize: "0.8rem",
                            border: "1px solid #1976d2",
                            borderRadius: 4,
                            background: "transparent",
                            color: "#1976d2",
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
              <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem", color: "#555" }}>
                Recent votes
              </h3>
              <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.9rem" }}>
                {votes.slice(0, 8).map((v, i) => (
                  <li key={i} style={{ marginBottom: 4 }}>
                    <span style={{ color: v.position === "Yes" ? "#2e7d32" : v.position === "No" ? "#c62828" : "#555" }}>
                      {v.position ?? "—"}
                    </span>
                    {v.description && ` · ${v.description.slice(0, 60)}${v.description.length > 60 ? "…" : ""}`}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {bills.length === 0 && votes.length === 0 && (
            <p style={{ color: "#555", fontSize: "0.9rem" }}>
              Bill and vote data may still be loading or unavailable for this member.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
