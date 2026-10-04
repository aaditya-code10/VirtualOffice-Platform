import { useCallback, useEffect, useState } from "react";
import { Cpu, Sparkles, ToggleLeft, ToggleRight } from "lucide-react";

import { ApiError, api, type Agent, type AuditEvent, type SystemStatus } from "../api";
import { useCanAdminister } from "../auth";
import { ErrorBanner, Header, Layout } from "../components/Layout";

export default function Settings() {
  const canEdit = useCanAdminister();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [a, s] = await Promise.all([api.getAgents(), api.systemStatus()]);
      setAgents(a);
      setStatus(s);
      if (canEdit) {
        try {
          setEvents(await api.getAuditEvents(40));
        } catch {
          setEvents([]);
        }
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load settings.");
    }
  }, [canEdit]);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggle(agent: Agent) {
    try {
      await api.updateAgent(agent.key, { enabled: !agent.enabled });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update that agent.");
    }
  }

  return (
    <Layout>
      <Header
        title="Settings & System Diagnostics"
        subtitle="AI reasoning engine telemetry, autonomous roster governance, and cryptographic audit logging."
      />

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "20px", marginBottom: "24px" }}>
        {/* Reasoning Core Diagnostics */}
        <div className="glass-panel" style={{ padding: "24px" }}>
          <div className="panel-head" style={{ borderBottom: "1px solid var(--glass-border)", paddingBottom: "12px", marginBottom: "16px" }}>
            <h4 style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "15px", fontWeight: 700, color: "#FFFFFF" }}>
              <Sparkles size={16} style={{ color: "var(--violet-bright)" }} /> Sovereign Reasoning Core
            </h4>
            <span className="grounded-tag">
              {status?.llm_enabled ? "● ONLINE" : "● DETERMINISTIC"}
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 14px", background: "rgba(255, 255, 255, 0.03)", borderRadius: "var(--radius-xs)", border: "1px solid var(--glass-border)" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Active Engine</span>
              <span style={{ fontSize: "12.5px", fontFamily: "var(--font-mono)", fontWeight: 700, color: "var(--violet-bright)" }}>
                {status?.engine.toUpperCase() || "GEMINI"}
              </span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 14px", background: "rgba(255, 255, 255, 0.03)", borderRadius: "var(--radius-xs)", border: "1px solid var(--glass-border)" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Model Identifier</span>
              <span style={{ fontSize: "12.5px", fontFamily: "var(--font-mono)", fontWeight: 700, color: "#FFFFFF" }}>
                {status?.llm_model || "gemini-3.1-flash-lite"}
              </span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 14px", background: "rgba(255, 255, 255, 0.03)", borderRadius: "var(--radius-xs)", border: "1px solid var(--glass-border)" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Database Persistence</span>
              <span style={{ fontSize: "12.5px", fontFamily: "var(--font-mono)", fontWeight: 600, color: "var(--success)" }}>
                {status?.database || "sqlite (virtual_office.db)"}
              </span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 14px", background: "rgba(255, 255, 255, 0.03)", borderRadius: "var(--radius-xs)", border: "1px solid var(--glass-border)" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>VirtualOffice Version</span>
              <span style={{ fontSize: "12.5px", fontFamily: "var(--font-mono)", fontWeight: 600, color: "var(--text-secondary)" }}>
                v{status?.version || "1.0.0"} · {status?.environment || "production"}
              </span>
            </div>
          </div>
        </div>

        {/* Specialist Roster Governance */}
        <div className="glass-panel" style={{ padding: "24px" }}>
          <div className="panel-head" style={{ borderBottom: "1px solid var(--glass-border)", paddingBottom: "12px", marginBottom: "16px" }}>
            <h4 style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "15px", fontWeight: 700, color: "#FFFFFF" }}>
              <Cpu size={16} style={{ color: "var(--soft-blue)" }} /> Agent Governance
            </h4>
            <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
              {agents.length} AGENTS CONFIGURED
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {agents.map((ag) => (
              <div
                key={ag.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 14px",
                  background: "rgba(255, 255, 255, 0.03)",
                  borderRadius: "var(--radius-xs)",
                  border: "1px solid var(--glass-border)",
                }}
              >
                <div>
                  <strong style={{ fontSize: "13px", color: "#FFFFFF", display: "block" }}>
                    {ag.name}
                  </strong>
                  <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    {ag.role} ({ag.department})
                  </span>
                </div>

                {canEdit && (
                  <button
                    type="button"
                    onClick={() => toggle(ag)}
                    style={{
                      background: "none",
                      border: "none",
                      color: ag.enabled ? "var(--success)" : "var(--text-muted)",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                      fontSize: "12px",
                      fontWeight: 600,
                    }}
                  >
                    {ag.enabled ? <ToggleRight size={22} /> : <ToggleLeft size={22} />}
                    <span>{ag.enabled ? "ENABLED" : "PAUSED"}</span>
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Audit Trail */}
      {canEdit && (
        <section className="glass-panel" style={{ padding: "24px" }}>
          <div className="panel-head">
            <h2>Cryptographic Audit Trail ({events.length})</h2>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "360px", overflowY: "auto" }}>
            {events.map((ev) => (
              <div
                key={ev.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 14px",
                  background: "rgba(255, 255, 255, 0.02)",
                  borderRadius: "var(--radius-xs)",
                  border: "1px solid var(--glass-border)",
                  fontSize: "12px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span style={{ fontFamily: "var(--font-mono)", color: "var(--violet-bright)", fontWeight: 700 }}>
                    {ev.action}
                  </span>
                  <span style={{ color: "var(--text-secondary)" }}>
                    by {ev.actor_label}
                  </span>
                </div>
                <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-muted)", fontSize: "11px" }}>
                  {new Date(ev.at).toLocaleString("en-IN")}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </Layout>
  );
}
