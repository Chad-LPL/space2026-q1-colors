import { useState, useEffect } from "react";
import type { Member, MemberBill } from "./api";
import {
  getScripts,
  getScript,
  generateScript,
  getContactStats,
  recordContactEvent,
  getMemberBills,
} from "./api";

interface Props {
  member: Member;
  onClose: () => void;
  initialIssue?: string;
  initialBillId?: string;
}

export default function ScriptFlow({ member, onClose, initialIssue, initialBillId }: Props) {
  const [scripts, setScripts] = useState<Array<{ id: number; title: string; billId?: string | null; issueSlug?: string | null }>>([]);
  const [selectedScriptId, setSelectedScriptId] = useState<number | null>(null);
  const [customIssue, setCustomIssue] = useState(initialIssue ?? "");
  const [emailBody, setEmailBody] = useState("");
  const [callScript, setCallScript] = useState("");
  const [subject, setSubject] = useState("");
  const [loading, setLoading] = useState(false);
  const [generateMessage, setGenerateMessage] = useState<string | null>(null);
  const [stats, setStats] = useState<{ last7Days: number; last30Days: number } | null>(null);
  const [issueForStats, setIssueForStats] = useState<string | null>(null);
  const [bills, setBills] = useState<MemberBill[]>([]);

  useEffect(() => {
    if (initialIssue != null) setCustomIssue(initialIssue);
  }, [initialIssue]);

  useEffect(() => {
    getScripts().then((r) => setScripts(r.scripts));
  }, []);

  useEffect(() => {
    if (!member?.id) return;
    getContactStats(member.id).then((s) => {
      if (s) setStats({ last7Days: s.last7Days, last30Days: s.last30Days });
    });
  }, [member?.id]);

  useEffect(() => {
    if (!member?.id) return;
    getMemberBills(member.id).then((r) => setBills(r.bills ?? []));
  }, [member?.id]);

  async function loadSeedScript(id: number) {
    setSelectedScriptId(id);
    setCustomIssue("");
    setGenerateMessage(null);
    const script = await getScript(id);
    if (script) {
      setIssueForStats(script.issueSlug || script.billId || null);
      if (script.issueSlug || script.billId) {
        getContactStats(member.id, script.billId ?? undefined, script.issueSlug ?? undefined).then((s) => {
          if (s) setStats({ last7Days: s.last7Days, last30Days: s.last30Days });
        });
      }
      // Generate detailed script via LLM instead of showing short seed body
      setEmailBody("");
      setCallScript("");
      setSubject("");
      await runGenerate(scripts.find((s) => s.id === id) ?? null, undefined, undefined);
    }
  }

  async function runGenerate(
    selected: { id: number; title: string; billId?: string | null; issueSlug?: string | null } | null,
    overrideIssueText: string | undefined,
    overrideBillId: string | undefined,
  ) {
    setLoading(true);
    setGenerateMessage(null);
    try {
      const res = await generateScript({
        memberId: member.id,
        issueText: (overrideIssueText ?? customIssue.trim()) || undefined,
        issueOrBillId: selected ? (selected.issueSlug || selected.billId || undefined) : (overrideBillId ?? initialBillId ?? undefined),
        issueTitle: selected ? selected.title : (initialIssue ?? (overrideIssueText ?? customIssue.trim()) || undefined),
        scriptId: selected?.id ?? selectedScriptId ?? undefined,
      });
      setEmailBody(res.emailBody);
      setCallScript(res.callScript);
      setSubject(res.subject || "Constituent request");
      if (res.message) setGenerateMessage(res.message);
      setIssueForStats(selected ? (selected.issueSlug || selected.billId || null) : (overrideIssueText ?? customIssue.trim()) || null);
      if (overrideIssueText ?? customIssue.trim()) {
        getContactStats(member.id, undefined, overrideIssueText ?? customIssue.trim()).then((s) => {
          if (s) setStats({ last7Days: s.last7Days, last30Days: s.last30Days });
        });
      } else if (selected?.issueSlug || selected?.billId) {
        getContactStats(member.id, selected?.billId ?? undefined, selected?.issueSlug ?? undefined).then((s) => {
          if (s) setStats({ last7Days: s.last7Days, last30Days: s.last30Days });
        });
      }
    } catch (err) {
      setGenerateMessage(err instanceof Error ? err.message : "Failed to generate script. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerate() {
    const selected = selectedScriptId != null ? scripts.find((s) => s.id === selectedScriptId) : null;
    await runGenerate(selected, undefined, undefined);
  }

  function handleSendEmail() {
    const topic = issueForStats || customIssue.trim() || "general";
    recordContactEvent({
      memberId: member.id,
      topic: topic || undefined,
      contactType: "email",
    });
    const maxLen = 1800;
    let body = emailBody;
    if (body.length > maxLen) {
      body = body.slice(0, maxLen - 30) + "\n\n[Message truncated for mailto link.]";
    }
    const mailto = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.location.href = mailto;
  }

  function handleCall() {
    const topic = issueForStats || customIssue.trim() || "general";
    recordContactEvent({
      memberId: member.id,
      topic: topic || undefined,
      contactType: "call",
    });
    // User will call; we've recorded. Show phone and script.
  }

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
          maxWidth: 560,
          width: "100%",
          maxHeight: "90vh",
          overflow: "auto",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ padding: "1rem 1.25rem", borderBottom: "1px solid #e0e0e0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Contact {member.name}</h2>
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
          {stats != null && (stats.last7Days > 0 || stats.last30Days > 0) && (
            <p style={{ fontSize: "0.9rem", color: "#555", marginBottom: "1rem" }}>
              {stats.last7Days} constituent{stats.last7Days !== 1 ? "s" : ""} contacted {member.name} about this topic in the last week.
              {stats.last30Days > 0 && ` ${stats.last30Days} in the last month.`}
            </p>
          )}

          <div style={{ marginBottom: "1rem" }}>
            <label style={{ display: "block", fontSize: "0.9rem", color: "#555", marginBottom: 4 }}>
              Pick a topic or describe an issue
            </label>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "0.5rem" }}>
              {scripts.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => loadSeedScript(s.id)}
                  style={{
                    padding: "0.4rem 0.75rem",
                    fontSize: "0.85rem",
                    border: selectedScriptId === s.id ? "1px solid #1976d2" : "1px solid #e0e0e0",
                    borderRadius: 6,
                    background: selectedScriptId === s.id ? "rgba(25,118,210,0.15)" : "transparent",
                    color: "#1a1a1a",
                    cursor: "pointer",
                  }}
                >
                  {s.title}
                </button>
              ))}
            </div>
            {bills.length > 0 && (
              <div style={{ marginBottom: "0.5rem" }}>
                <span style={{ fontSize: "0.85rem", color: "#555", marginRight: "0.5rem" }}>Or a bill they sponsor:</span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginTop: 4 }}>
                  {bills.slice(0, 8).map((b, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => {
                        setSelectedScriptId(null);
                        setCustomIssue(b.title || b.number || "this bill");
                        setGenerateMessage(null);
                        runGenerate(null, b.title || b.number || "this bill", b.number ?? undefined);
                      }}
                      style={{
                        padding: "0.35rem 0.6rem",
                        fontSize: "0.8rem",
                        border: "1px solid #e0e0e0",
                        borderRadius: 6,
                        background: "transparent",
                        color: "#1a1a1a",
                        cursor: "pointer",
                        maxWidth: "100%",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                      title={b.title || b.number || undefined}
                    >
                      {b.number ? `${b.number}${b.status ? ` (${b.status})` : ""}` : (b.title || "Bill").slice(0, 40)}
                    </button>
                  ))}
                </div>
              </div>
            )}
            <input
              type="text"
              value={customIssue}
              onChange={(e) => setCustomIssue(e.target.value)}
              placeholder="Or type an issue (e.g. climate, healthcare)"
              style={{
                width: "100%",
                padding: "0.5rem 0.75rem",
                fontSize: "1rem",
                border: "1px solid #e0e0e0",
                borderRadius: 6,
                background: "#f5f5f5",
                color: "#1a1a1a",
              }}
            />
            <button
              type="button"
              onClick={handleGenerate}
              disabled={loading}
              style={{
                marginTop: "0.5rem",
                padding: "0.5rem 1rem",
                fontSize: "0.9rem",
                border: "none",
                borderRadius: 6,
                background: "#1976d2",
                color: "#fff",
                cursor: loading ? "not-allowed" : "pointer",
              }}
            >
              {loading ? "Generating…" : "Generate script"}
            </button>
            {generateMessage && (
              <p style={{ fontSize: "0.85rem", color: "#c62828", marginTop: "0.5rem", marginBottom: 0 }}>
                {generateMessage}
              </p>
            )}
          </div>

          <div style={{ marginBottom: "1rem" }}>
            <label style={{ display: "block", fontSize: "0.9rem", color: "#555", marginBottom: 4 }}>
              Email (edit if you like)
            </label>
            <textarea
              value={emailBody}
              onChange={(e) => setEmailBody(e.target.value)}
              rows={4}
              style={{
                width: "100%",
                padding: "0.5rem 0.75rem",
                fontSize: "0.95rem",
                border: "1px solid #e0e0e0",
                borderRadius: 6,
                background: "#f5f5f5",
                color: "#1a1a1a",
                resize: "vertical",
              }}
            />
            <button
              type="button"
              onClick={handleSendEmail}
              style={{
                marginTop: "0.5rem",
                padding: "0.5rem 1rem",
                fontSize: "0.9rem",
                border: "none",
                borderRadius: 6,
                background: "#1976d2",
                color: "#fff",
                cursor: "pointer",
              }}
            >
              Open email
            </button>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.9rem", color: "#555", marginBottom: 4 }}>
              Call script (what to say)
            </label>
            <textarea
              value={callScript}
              onChange={(e) => setCallScript(e.target.value)}
              rows={3}
              style={{
                width: "100%",
                padding: "0.5rem 0.75rem",
                fontSize: "0.95rem",
                border: "1px solid #e0e0e0",
                borderRadius: 6,
                background: "#f5f5f5",
                color: "#1a1a1a",
                resize: "vertical",
              }}
            />
            <p style={{ fontSize: "0.85rem", color: "#555", marginTop: 4 }}>
              Staff usually answer. Say you're a constituent and you can read the script or use your own words.
            </p>
            {member.phone && (
              <p style={{ marginTop: "0.5rem" }}>
                📞 <strong>{member.phone}</strong>
              </p>
            )}
            <button
              type="button"
              onClick={handleCall}
              style={{
                marginTop: "0.5rem",
                padding: "0.5rem 1rem",
                fontSize: "0.9rem",
                border: "1px solid #1976d2",
                borderRadius: 6,
                background: "transparent",
                color: "#1976d2",
                cursor: "pointer",
              }}
            >
              I'm calling (record my contact)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
