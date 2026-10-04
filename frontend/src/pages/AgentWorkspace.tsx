import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Brain,
  Cpu,
  Gauge,
  Loader2,
  Send,
  Sparkles,
  Target,
  Crown,
  CheckCircle2,
  Clock,
  Building,
} from "lucide-react";

import { ApiError, api, type Agent, type WorkOrder } from "../api";
import { useAuth } from "../auth";
import { Empty, ErrorBanner, Layout } from "../components/Layout";
import { WorkOrderModal } from "../components/WorkOrderModal";

interface HistoryItem {
  id: string;
  work_order_id: string;
  command: string;
  finding: string | null;
  recommended_action: string | null;
  confidence: number;
  evidence: string[];
  duration_ms: number;
  created_at: string;
}

export default function AgentWorkspace() {
  const { agentKey = "" } = useParams();
  const { company } = useAuth();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [command, setCommand] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<WorkOrder | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [a, tasks] = await Promise.all([api.getAgent(agentKey), api.getAgentTasks(agentKey)]);
      setAgent(a);
      setHistory(tasks);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load this workstation.");
    }
  }, [agentKey]);

  useEffect(() => {
    void load();
  }, [load]);

  async function brief() {
    const text = command.trim();
    if (!text || running) return;

    setRunning(true);
    setError(null);
    try {
      const order = await api.createWorkOrder(text, agentKey);
      setResult(order);
      setCommand("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The assignment failed.");
    } finally {
      setRunning(false);
    }
  }

  const getIcon = () => {
    if (agent?.is_synthesizer) return <Crown size={32} />;
    switch (agentKey) {
      case "business_strategy":
        return <Cpu size={32} />;
      case "market_research":
        return <Target size={32} />;
      case "finance":
        return <Gauge size={32} />;
      case "marketing":
        return <Sparkles size={32} />;
      default:
        return <Brain size={32} />;
    }
  };

  return (
    <Layout>
      <div style={{ marginBottom: "16px" }}>
        <Link
          to="/office"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            color: "var(--violet-bright)",
            fontSize: "12.5px",
            fontWeight: 600,
          }}
        >
          <ArrowLeft size={14} /> Back to Workforce Floorplan
        </Link>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {/* ── Large Glass Identity Header ─────────────────────────────────── */}
      <section className="glass-panel glass-panel--glow" style={{ padding: "30px", marginBottom: "24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
            <div
              style={{
                width: "68px",
                height: "68px",
                borderRadius: "18px",
                background: "linear-gradient(135deg, rgba(139, 92, 255, 0.3) 0%, rgba(91, 140, 255, 0.2) 100%)",
                border: "1px solid rgba(255, 255, 255, 0.2)",
                display: "grid",
                placeItems: "center",
                color: "#FFFFFF",
                boxShadow: "0 6px 20px rgba(139, 92, 255, 0.35)",
              }}
            >
              {getIcon()}
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
                <h1 style={{ fontFamily: "var(--font-display)", fontSize: "26px", fontWeight: 700, color: "#FFFFFF" }}>
                  {agent?.name ?? "Specialist Workstation"}
                </h1>
                <span className="agent-department-badge">
                  {agent?.department.toUpperCase()}
                </span>
                {agent?.is_synthesizer && (
                  <span className="role-tag-master">MANAGING PARTNER</span>
                )}
              </div>
              <p style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
                {agent?.role}
              </p>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <div className="agent-status-indicator status-online" style={{ padding: "6px 14px", fontSize: "12px" }}>
              <span className="status-ping" />
              <span>{agent?.status.toUpperCase() || "ONLINE"}</span>
            </div>
            <div style={{ background: "rgba(255, 255, 255, 0.05)", border: "1px solid var(--glass-border)", borderRadius: "var(--radius-sm)", padding: "8px 14px", textAlign: "right" }}>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--text-muted)" }}>COGNITION HEALTH</div>
              <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--success)" }}>{agent?.health}%</div>
            </div>
          </div>
        </div>

        {/* Company Twin Context Injected */}
        <div style={{ marginTop: "24px", paddingTop: "18px", borderTop: "1px solid var(--glass-border)", display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap", fontSize: "12.5px", color: "var(--text-muted)" }}>
          <Building size={14} style={{ color: "var(--soft-blue)" }} />
          <span>Active Context: <strong style={{ color: "var(--text-primary)" }}>{company?.name || "Workspace"}</strong></span>
          <span>·</span>
          <span>Industry: <strong style={{ color: "var(--text-secondary)" }}>{company?.industry || "Venture"}</strong></span>
          <span>·</span>
          <span>Core Remit: <strong style={{ color: "var(--violet-bright)" }}>{agent?.focus}</strong></span>
        </div>
      </section>

      {/* ── Direct Briefing / Task Console ─────────────────────────────── */}
      <section className="glass-panel" style={{ padding: "24px", marginBottom: "24px" }}>
        <h3 style={{ fontFamily: "var(--font-display)", fontSize: "17px", fontWeight: 700, color: "#FFFFFF", marginBottom: "8px" }}>
          Task {agent?.name || "Specialist"} Directly
        </h3>
        <p style={{ fontSize: "13px", color: "var(--text-muted)", marginBottom: "16px" }}>
          Assign a focused strategic question, financial model evaluation, or analysis. Results will be synthesized into the executive archive.
        </p>

        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <input
            className="glass-input"
            value={command}
            placeholder={`Ask ${agent?.name || "specialist"} for a direct deep evaluation…`}
            onChange={(e) => setCommand(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && brief()}
            disabled={running}
            style={{ flex: 1 }}
          />
          <button
            type="button"
            className="btn-primary"
            onClick={brief}
            disabled={running || !command.trim()}
          >
            {running ? (
              <>
                <Loader2 size={15} className="spin" />
                <span>Evaluating…</span>
              </>
            ) : (
              <>
                <span>Send Brief</span>
                <Send size={14} />
              </>
            )}
          </button>
        </div>
      </section>

      {/* ── Past Work & Advisory History ────────────────────────────────── */}
      <section className="glass-panel" style={{ padding: "24px" }}>
        <div className="panel-head">
          <h2>Specialist Advisory Deliverables</h2>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-muted)" }}>
            {history.length} EVALUATIONS RECORDED
          </span>
        </div>

        {history.length === 0 ? (
          <Empty
            icon={<Clock size={24} />}
            text={`${agent?.name || "This specialist"} has not been tasked with direct assignments yet.`}
          />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            {history.map((item) => (
              <div
                key={item.id}
                className="glass-card"
                style={{ padding: "18px 20px" }}
              >
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "10px" }}>
                  <strong style={{ fontSize: "14px", color: "var(--text-primary)" }}>
                    {item.command}
                  </strong>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-muted)" }}>
                    {new Date(item.created_at).toLocaleDateString("en-IN", {
                      day: "numeric",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>

                {item.finding && (
                  <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.55", marginBottom: "12px" }}>
                    {item.finding}
                  </p>
                )}

                {item.recommended_action && (
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", background: "rgba(139, 92, 255, 0.12)", border: "1px solid rgba(139, 92, 255, 0.3)", padding: "8px 12px", borderRadius: "var(--radius-xs)", fontSize: "12.5px", color: "var(--violet-bright)" }}>
                    <CheckCircle2 size={14} style={{ color: "var(--success)", flexShrink: 0 }} />
                    <span><strong>Recommendation:</strong> {item.recommended_action}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {result && <WorkOrderModal order={result} onClose={() => setResult(null)} />}
    </Layout>
  );
}
