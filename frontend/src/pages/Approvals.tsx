import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, ShieldCheck, XCircle } from "lucide-react";

import { ApiError, api, type Approval } from "../api";
import { useCanAdminister } from "../auth";
import { Empty, ErrorBanner, Header, Layout } from "../components/Layout";

export default function Approvals() {
  const canDecide = useCanAdminister();
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [comments, setComments] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setApprovals(await api.getApprovals());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load approvals.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function decide(id: string, decision: "approve" | "reject" | "changes") {
    setBusy(id);
    setError(null);
    try {
      await api.decideApproval(id, decision, comments[id]);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not record that decision.");
    } finally {
      setBusy(null);
    }
  }

  const pending = approvals.filter((a) => a.status === "PENDING");
  const decided = approvals.filter((a) => a.status !== "PENDING");

  return (
    <Layout>
      <Header
        title="Executive Governance & Resource Gatekeeping"
        subtitle="Human-in-the-loop authorizations: strategic recommendations that commit capital, alter pricing, or recruit talent pause here for approval."
      />

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {/* Governance Summary Grid */}
      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "24px" }}>
        <div className="apex-kpi-card">
          <span className="apex-kpi-label">PENDING AUTHORIZATIONS</span>
          <div className="apex-kpi-value" style={{ color: pending.length > 0 ? "var(--warning)" : "var(--success)" }}>
            {pending.length}
          </div>
          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Awaiting executive sign-off</span>
        </div>

        <div className="apex-kpi-card">
          <span className="apex-kpi-label">HIGH RISK EXPOSURE</span>
          <div className="apex-kpi-value" style={{ color: "var(--error)" }}>
            {pending.filter((p) => p.risk.toLowerCase() === "high" || p.risk.toLowerCase() === "critical").length}
          </div>
          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Capital or legal sensitivity</span>
        </div>

        <div className="apex-kpi-card">
          <span className="apex-kpi-label">HISTORICAL RULINGS</span>
          <div className="apex-kpi-value" style={{ color: "var(--violet-bright)" }}>
            {decided.length}
          </div>
          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Archived audit decisions</span>
        </div>
      </section>

      {/* Pending Reviews */}
      <section className="glass-panel" style={{ padding: "24px", marginBottom: "24px" }}>
        <div className="panel-head">
          <h2>Pending Review Actions ({pending.length})</h2>
        </div>

        {pending.length === 0 ? (
          <Empty
            icon={<ShieldCheck size={26} />}
            text="No actions currently awaiting executive authorization."
          />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {pending.map((item) => (
              <div
                key={item.id}
                className="glass-card"
                style={{ padding: "20px" }}
              >
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "12px", flexWrap: "wrap", gap: "12px" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                      <span
                        className="grounded-tag"
                        style={{
                          background: item.risk === "High" ? "rgba(255, 107, 122, 0.15)" : "rgba(255, 209, 102, 0.15)",
                          color: item.risk === "High" ? "var(--error)" : "var(--warning)",
                          borderColor: item.risk === "High" ? "rgba(255, 107, 122, 0.35)" : "rgba(255, 209, 102, 0.35)",
                        }}
                      >
                        {item.risk.toUpperCase()} RISK
                      </span>
                      <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                        Proposer: {item.owner}
                      </span>
                    </div>
                    <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF" }}>
                      {item.title}
                    </h3>
                  </div>

                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-muted)" }}>
                    {new Date(item.created_at).toLocaleDateString("en-IN", {
                      day: "numeric",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>

                {item.description && (
                  <p style={{ fontSize: "13.5px", color: "var(--text-secondary)", lineHeight: "1.6", marginBottom: "12px" }}>
                    {item.description}
                  </p>
                )}

                {item.expected_impact && (
                  <div style={{ padding: "8px 12px", background: "rgba(255, 255, 255, 0.04)", borderRadius: "var(--radius-xs)", fontSize: "12px", color: "var(--text-muted)", marginBottom: "16px" }}>
                    <strong>Anticipated Impact:</strong> {item.expected_impact}
                  </div>
                )}

                {canDecide && (
                  <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap", paddingTop: "12px", borderTop: "1px solid var(--glass-border)" }}>
                    <input
                      className="glass-input"
                      placeholder="Optional executive rationale / condition…"
                      value={comments[item.id] || ""}
                      onChange={(e) => setComments({ ...comments, [item.id]: e.target.value })}
                      style={{ flex: 1, minWidth: "220px", height: "38px" }}
                    />
                    <button
                      type="button"
                      className="glass-btn glass-btn--success glass-btn--sm"
                      onClick={() => decide(item.id, "approve")}
                      disabled={busy === item.id}
                    >
                      <CheckCircle2 size={14} /> Authorize
                    </button>
                    <button
                      type="button"
                      className="glass-btn glass-btn--danger glass-btn--sm"
                      onClick={() => decide(item.id, "reject")}
                      disabled={busy === item.id}
                    >
                      <XCircle size={14} /> Deny
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Historical Resolved Log */}
      {decided.length > 0 && (
        <section className="glass-panel" style={{ padding: "24px" }}>
          <div className="panel-head">
            <h2>Resolved Governance Audit Trail ({decided.length})</h2>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {decided.map((item) => (
              <div key={item.id} className="glass-card" style={{ padding: "14px 18px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <strong style={{ fontSize: "13.5px", color: "#FFFFFF", display: "block" }}>
                    {item.title}
                  </strong>
                  <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    Owner: {item.owner} · Decided on {item.decided_at ? new Date(item.decided_at).toLocaleDateString("en-IN") : "N/A"}
                  </span>
                </div>
                <span className={`verdict-badge ${item.status === "APPROVED" ? "go" : "nogo"}`}>
                  {item.status}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </Layout>
  );
}
