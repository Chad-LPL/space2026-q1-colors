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
  const partyColor = party === "D" ? "#1565c0" : party === "R" ? "#c62828" : "#555";

  return (
    <div
      style={{
        padding: "0.75rem 1rem",
        borderBottom: "1px solid #e0e0e0",
        background: "#fff",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
        <div>
          <div style={{ fontSize: "0.75rem", color: "#555", marginBottom: 2 }}>{role}</div>
          <button
            type="button"
            onClick={onSelect}
            style={{
              background: "none",
              border: "none",
              padding: 0,
              color: "#1a1a1a",
              fontSize: "1rem",
              fontWeight: 600,
              cursor: "pointer",
              textAlign: "left",
            }}
          >
            {member.name}
          </button>
          <div style={{ fontSize: "0.85rem", color: partyColor, marginTop: 2 }}>{party}</div>
          {member.phone && (
            <div style={{ fontSize: "0.85rem", color: "#555", marginTop: 4 }}>
              📞 {member.phone}
            </div>
          )}
          {(member.nextElection != null || member.firstElected != null) && (
            <div style={{ fontSize: "0.8rem", color: "#555", marginTop: 2 }}>
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
            padding: "0.35rem 0.6rem",
            fontSize: "0.85rem",
            border: "1px solid #1976d2",
            borderRadius: 4,
            background: "transparent",
            color: "#1976d2",
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
      <div style={{ padding: "0.75rem 1rem", borderBottom: "1px solid #e0e0e0", flexShrink: 0 }}>
        <div style={{ fontSize: "0.9rem", color: "#555" }}>District</div>
        <div style={{ fontWeight: 600, color: "#1a1a1a" }}>{districtInfo.districtLabel}</div>
        <div style={{ fontSize: "0.85rem", color: "#555" }}>{districtInfo.label}</div>
      </div>

      {(!representative && senators.length === 0) && (
        <div style={{ padding: "0.75rem 1rem", color: "#555", fontSize: "0.9rem", borderBottom: "1px solid #e0e0e0" }}>
          {membersErrorProp ? (
            <>{membersErrorProp} <a href="https://api.data.gov/signup" target="_blank" rel="noopener noreferrer" style={{ color: "#1976d2" }}>api.data.gov</a></>
          ) : (
            <>
              Member data is loading or unavailable. Add <code style={{ fontSize: "0.85em" }}>CONGRESS_API_KEY</code> to <code style={{ fontSize: "0.85em" }}>backend/.env</code> (get a free key at{" "}
              <a href="https://api.data.gov/signup" target="_blank" rel="noopener noreferrer" style={{ color: "#1976d2" }}>api.data.gov</a>) and restart the backend.
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

      <div style={{ padding: "1rem", marginTop: "auto", borderTop: "1px solid #e0e0e0" }}>
        <button
          type="button"
          onClick={onSendPostcard}
          style={{
            width: "100%",
            padding: "0.6rem 1rem",
            fontSize: "0.95rem",
            border: "1px dashed #bdbdbd",
            borderRadius: 6,
            background: "transparent",
            color: "#555",
            cursor: "pointer",
          }}
        >
          📮 Send a postcard (coming soon)
        </button>
      </div>
    </div>
  );
}
