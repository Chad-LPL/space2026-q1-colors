import type { Member, DistrictInfo } from "./api";

interface Props {
  districtInfo: DistrictInfo;
  representative: Member | null;
  senators: Member[];
  /** When API key is set but Congress returned no members */
  membersError?: string;
  onSelectMember: (m: Member) => void;
  onContactMember: (m: Member) => void;
  onSendPostcard: () => void;
}

function MemberCard({
  member,
  role,
  onSelect,
  onContact,
}: {
  member: Member;
  role: string;
  onSelect: () => void;
  onContact: () => void;
}) {
  const party = member.party === "Republican" || member.party === "R" ? "R" : member.party === "Democratic" || member.party === "D" ? "D" : member.party ?? "—";
  const partyColor = party === "D" ? "var(--color-party-d)" : party === "R" ? "var(--color-party-r)" : "var(--color-text-muted)";

  return (
    <div
      style={{
        padding: "var(--space-3) var(--space-4)",
        borderBottom: "1px solid var(--color-border)",
        background: "var(--color-surface)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "var(--space-2)" }}>
        <div>
          <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-secondary)", marginBottom: 2 }}>{role}</div>
          <button
            type="button"
            onClick={onSelect}
            style={{
              background: "none",
              border: "none",
              padding: 0,
              color: "var(--color-text)",
              fontSize: "var(--text-base)",
              fontWeight: "var(--font-semibold)",
              cursor: "pointer",
              textAlign: "left",
            }}
          >
            {member.name}
          </button>
          <div style={{ fontSize: "var(--text-sm)", color: partyColor, marginTop: 2 }}>{party}</div>
          {member.phone && (
            <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", marginTop: "var(--space-1)" }}>
              📞 {member.phone}
            </div>
          )}
          {(member.nextElection != null || member.firstElected != null) && (
            <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-secondary)", marginTop: 2 }}>
              {member.nextElection != null && `Next election: ${member.nextElection}`}
              {member.nextElection != null && member.firstElected != null && " · "}
              {member.firstElected != null && `First elected: ${member.firstElected}`}
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={onContact}
          style={{
            padding: "var(--space-1) var(--space-2)",
            fontSize: "var(--text-sm)",
            border: "1px solid var(--color-primary)",
            borderRadius: "var(--radius-sm)",
            background: "transparent",
            color: "var(--color-primary)",
            cursor: "pointer",
            flexShrink: 0,
          }}
        >
          Contact
        </button>
      </div>
    </div>
  );
}

export default function MemberCards({
  districtInfo,
  representative,
  senators,
  membersError: membersErrorProp,
  onSelectMember,
  onContactMember,
  onSendPostcard,
}: Props) {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "auto" }}>
      <div style={{ padding: "var(--space-3) var(--space-4)", borderBottom: "1px solid var(--color-border)", flexShrink: 0 }}>
        <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)" }}>District</div>
        <div style={{ fontWeight: "var(--font-semibold)", color: "var(--color-text)" }}>{districtInfo.districtLabel}</div>
        <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)" }}>{districtInfo.label}</div>
      </div>

      {(!representative && senators.length === 0) && (
        <div style={{ padding: "var(--space-3) var(--space-4)", color: "var(--color-text-secondary)", fontSize: "var(--text-sm)", borderBottom: "1px solid var(--color-border)" }}>
          {membersErrorProp ? (
            <>{membersErrorProp} <a href="https://api.data.gov/signup" target="_blank" rel="noopener noreferrer">api.data.gov</a></>
          ) : (
            <>
              Member data is loading or unavailable. Add <code style={{ fontSize: "0.85em" }}>CONGRESS_API_KEY</code> to <code style={{ fontSize: "0.85em" }}>backend/.env</code> (get a free key at{" "}
              <a href="https://api.data.gov/signup" target="_blank" rel="noopener noreferrer">api.data.gov</a>) and restart the backend.
            </>
          )}
        </div>
      )}

      {representative && (
        <MemberCard
          member={representative}
          role="Representative"
          onSelect={() => onSelectMember(representative)}
          onContact={() => onContactMember(representative)}
        />
      )}
      {senators.map((s) => (
        <MemberCard
          key={s.id}
          member={s}
          role="Senator"
          onSelect={() => onSelectMember(s)}
          onContact={() => onContactMember(s)}
        />
      ))}

      <div style={{ padding: "var(--space-4)", marginTop: "auto", borderTop: "1px solid var(--color-border)" }}>
        <button
          type="button"
          onClick={onSendPostcard}
          style={{
            width: "100%",
            padding: "var(--space-2) var(--space-4)",
            fontSize: "var(--text-base)",
            border: "1px dashed var(--color-border)",
            borderRadius: "var(--radius-sm)",
            background: "transparent",
            color: "var(--color-text-secondary)",
            cursor: "pointer",
          }}
        >
          📮 Send a postcard (coming soon)
        </button>
      </div>
    </div>
  );
}
