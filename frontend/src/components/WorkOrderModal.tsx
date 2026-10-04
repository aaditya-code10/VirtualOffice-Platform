/** Full result of an executed work order, rendered as an Executive Briefing Dossier (Liquid Glass Design System). */
import { useState } from "react";
import {
  AlertTriangle,
  Download,
  Lightbulb,
  ListChecks,
  Printer,
  X,
  Activity,
  BrainCircuit,
  FileText,
} from "lucide-react";

import { type WorkOrder } from "../api";
import { Markdown } from "./Markdown";

const AGENT_LABELS: Record<string, string> = {
  business_strategy: "Business Strategy Advisor (Sarah Connor)",
  market_research: "Market Research Specialist (David Kim)",
  finance: "Financial Modeling Advisor (Arthur Pendelton)",
  marketing: "Go-to-Market Strategist (Sophia Chen)",
  strategy: "Managing Partner & Synthesizer (Jordan Blake)",
};

type Tab = "brief" | "agents" | "sources";

export function WorkOrderModal({ order, onClose }: { order: WorkOrder; onClose: () => void }) {
  const [tab, setTab] = useState<Tab>("brief");

  function downloadMarkdown() {
    const text =
      `# ${order.artifact_title || "Executive Business Evaluation Dossier"}\n\n` +
      `**Sector / Category:** ${order.category || "General Business"}\n` +
      `**Business Inquiry:** ${order.command}\n` +
      `**Viability / Confidence:** ${order.confidence}%\n` +
      `**Strategic Verdict:** ${order.recommendation || "N/A"}\n` +
      `**Evaluation Date:** ${new Date(order.created_at).toLocaleString("en-IN")}\n\n` +
      `---\n\n` +
      `## Executive Summary\n\n` +
      `${order.summary || ""}\n\n` +
      `---\n\n` +
      `## Strategic Recommendation & Verdict\n\n` +
      `**Verdict:** ${order.recommendation || "N/A"}\n\n` +
      (order.next_actions && order.next_actions.length
        ? `### Recommended Action Roadmap\n${order.next_actions.map((a, i) => `${i + 1}. ${a}`).join("\n")}\n\n`
        : "") +
      (order.risks && order.risks.length
        ? `### Key Strategic Risks\n${order.risks.map((r) => `- ${r}`).join("\n")}\n\n`
        : "") +
      (order.opportunities && order.opportunities.length
        ? `### Strategic Strengths & Opportunities\n${order.opportunities.map((o) => `- ${o}`).join("\n")}\n\n`
        : "") +
      `---\n\n` +
      `## Full Consulting Dossier\n\n` +
      `${order.artifact_body || ""}\n\n` +
      `---\n\n` +
      `## Specialist Advisory Contributions\n\n` +
      order.tasks
        .map(
          (t) =>
            `### ${AGENT_LABELS[t.agent_key] || t.agent_key}\n` +
            `**Analysis:** ${t.finding || "N/A"}\n\n` +
            `**Recommended Action:** ${t.recommended_action || "N/A"}\n\n` +
            (t.risks && t.risks.length
              ? `**Identified Risks:**\n${t.risks.map((r) => `- ${r}`).join("\n")}\n\n`
              : "") +
            (t.opportunities && t.opportunities.length
              ? `**Identified Opportunities:**\n${t.opportunities.map((o) => `- ${o}`).join("\n")}\n\n`
              : ""),
        )
        .join("\n");

    const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Executive_Dossier_${order.id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const hasAttachedPdf = Boolean(
    order.document_id || order.citations.some((c) => c.excerpt.includes("Attached Business Plan")),
  );

  return (
    <div className="glass-modal-backdrop" onClick={onClose} role="presentation">
      <div className="glass-modal-card" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" style={{ maxWidth: "880px" }}>
        {/* Header */}
        <div className="modal-header">
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", marginBottom: "8px" }}>
              <span className="grounded-tag">
                <Activity size={11} /> MULTI-AGENT ADVISORY
              </span>
              {order.category && (
                <span className="grounded-tag" style={{ background: "rgba(91, 140, 255, 0.15)", borderColor: "rgba(91, 140, 255, 0.4)", color: "var(--soft-blue)" }}>
                  {order.category}
                </span>
              )}
              {hasAttachedPdf && (
                <span className="grounded-tag" style={{ background: "rgba(139, 92, 255, 0.2)", borderColor: "rgba(139, 92, 255, 0.5)", color: "var(--violet-bright)" }}>
                  <FileText size={10} /> GROUNDED IN PROPOSAL PDF
                </span>
              )}
              <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                ID: {order.id.slice(0, 8)}
              </span>
            </div>

            <h2 style={{ fontSize: "18px", color: "#FFFFFF", lineHeight: "1.3" }}>
              {order.headline || order.command}
            </h2>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <button
              type="button"
              className="glass-btn glass-btn--secondary glass-btn--sm"
              onClick={downloadMarkdown}
              title="Download dossier as Markdown"
            >
              <Download size={13} />
              <span>Export .MD</span>
            </button>
            <button
              type="button"
              className="glass-btn glass-btn--secondary glass-btn--sm"
              onClick={() => window.print()}
              title="Print or export as PDF"
            >
              <Printer size={13} />
              <span>Print / PDF</span>
            </button>
            <button
              type="button"
              className="glass-modal-close-btn"
              onClick={onClose}
              aria-label="Close modal"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Tab Strip */}
        <div className="modal-tabs">
          <button
            type="button"
            className={`modal-tab ${tab === "brief" ? "active" : ""}`}
            onClick={() => setTab("brief")}
          >
            Executive Synthesis
          </button>
          <button
            type="button"
            className={`modal-tab ${tab === "agents" ? "active" : ""}`}
            onClick={() => setTab("agents")}
          >
            Specialist Perspectives ({order.tasks.length})
          </button>
          {order.citations && order.citations.length > 0 && (
            <button
              type="button"
              className={`modal-tab ${tab === "sources" ? "active" : ""}`}
              onClick={() => setTab("sources")}
            >
              Document Citations ({order.citations.length})
            </button>
          )}
        </div>

        {/* Body Content */}
        <div className="modal-body">
          {tab === "brief" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "22px" }}>
              {/* Verdict Banner */}
              {order.recommendation && (
                <div
                  style={{
                    background: "rgba(139, 92, 255, 0.12)",
                    border: "1px solid rgba(139, 92, 255, 0.35)",
                    borderRadius: "var(--radius-md)",
                    padding: "18px 22px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "16px",
                  }}
                >
                  <div>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "10.5px", color: "var(--text-muted)", letterSpacing: "0.08em" }}>
                      SYNTHESIZED EXECUTIVE VERDICT
                    </span>
                    <h3 style={{ fontFamily: "var(--font-display)", fontSize: "20px", fontWeight: 700, color: "#FFFFFF", marginTop: "2px" }}>
                      {order.recommendation}
                    </h3>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "10.5px", color: "var(--text-muted)" }}>
                      CONFIDENCE SCORE
                    </span>
                    <div style={{ fontSize: "22px", fontWeight: 700, color: "var(--success)" }}>
                      {order.confidence}%
                    </div>
                  </div>
                </div>
              )}

              {/* Summary */}
              {order.summary && (
                <div>
                  <h4 style={{ fontSize: "13px", fontFamily: "var(--font-mono)", color: "var(--violet-bright)", marginBottom: "8px", letterSpacing: "0.06em" }}>
                    EXECUTIVE SUMMARY
                  </h4>
                  <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: "1.65" }}>
                    {order.summary}
                  </p>
                </div>
              )}

              {/* Next Actions Roadmap */}
              {order.next_actions && order.next_actions.length > 0 && (
                <div className="glass-panel" style={{ padding: "18px 20px" }}>
                  <h4 style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13.5px", fontWeight: 700, color: "var(--success)", marginBottom: "12px" }}>
                    <ListChecks size={16} /> RECOMMENDED ACTION ROADMAP
                  </h4>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {order.next_actions.map((act, i) => (
                      <div key={i} style={{ display: "flex", gap: "10px", fontSize: "13px", color: "var(--text-primary)" }}>
                        <span style={{ fontFamily: "var(--font-mono)", color: "var(--violet-bright)", fontWeight: 700 }}>
                          {String(i + 1).padStart(2, "0")}.
                        </span>
                        <span>{act}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Risks & Opportunities Grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                {order.risks && order.risks.length > 0 && (
                  <div className="glass-panel" style={{ padding: "16px", borderColor: "rgba(255, 107, 122, 0.25)" }}>
                    <h5 style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", fontFamily: "var(--font-mono)", color: "var(--error)", marginBottom: "10px" }}>
                      <AlertTriangle size={14} /> IDENTIFIED STRATEGIC RISKS
                    </h5>
                    <ul style={{ paddingLeft: "16px", fontSize: "12.5px", color: "var(--text-secondary)", lineHeight: "1.5" }}>
                      {order.risks.map((r, i) => (
                        <li key={i} style={{ marginBottom: "6px" }}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {order.opportunities && order.opportunities.length > 0 && (
                  <div className="glass-panel" style={{ padding: "16px", borderColor: "rgba(124, 255, 178, 0.25)" }}>
                    <h5 style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", fontFamily: "var(--font-mono)", color: "var(--success)", marginBottom: "10px" }}>
                      <Lightbulb size={14} /> STRATEGIC OPPORTUNITIES
                    </h5>
                    <ul style={{ paddingLeft: "16px", fontSize: "12.5px", color: "var(--text-secondary)", lineHeight: "1.5" }}>
                      {order.opportunities.map((o, i) => (
                        <li key={i} style={{ marginBottom: "6px" }}>{o}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Full Artifact Body */}
              {order.artifact_body && (
                <div style={{ marginTop: "12px" }}>
                  <h4 style={{ fontSize: "13px", fontFamily: "var(--font-mono)", color: "var(--violet-bright)", marginBottom: "10px", letterSpacing: "0.06em" }}>
                    COMPLETE DELIVERABLE DOSSIER
                  </h4>
                  <div className="glass-panel" style={{ padding: "22px", background: "rgba(0, 0, 0, 0.3)" }}>
                    <Markdown source={order.artifact_body} />
                  </div>
                </div>
              )}
            </div>
          )}

          {tab === "agents" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {order.tasks.map((task) => (
                <div key={task.id} className="glass-panel" style={{ padding: "20px" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <BrainCircuit size={16} style={{ color: "var(--violet-bright)" }} />
                      <strong style={{ fontSize: "14.5px", color: "#FFFFFF" }}>
                        {AGENT_LABELS[task.agent_key] || task.agent_key}
                      </strong>
                    </div>
                    <span className="grounded-tag">
                      {task.confidence}% CONFIDENCE
                    </span>
                  </div>

                  {task.finding && (
                    <p style={{ fontSize: "13.5px", color: "var(--text-secondary)", lineHeight: "1.6", marginBottom: "12px" }}>
                      {task.finding}
                    </p>
                  )}

                  {task.recommended_action && (
                    <div style={{ padding: "10px 14px", background: "rgba(139, 92, 255, 0.12)", border: "1px solid rgba(139, 92, 255, 0.3)", borderRadius: "var(--radius-xs)", fontSize: "13px", color: "var(--violet-bright)" }}>
                      <strong>Action Recommendation:</strong> {task.recommended_action}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {tab === "sources" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {order.citations.map((cite, i) => (
                <div key={i} className="glass-panel" style={{ padding: "16px 18px" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12.5px", color: "var(--soft-blue)", fontWeight: 600 }}>
                      <FileText size={14} />
                      <span>{cite.filename}</span>
                    </div>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-muted)" }}>
                      Chunk #{cite.chunk} · Score {cite.score.toFixed(2)}
                    </span>
                  </div>
                  <blockquote style={{ fontSize: "12.5px", color: "var(--text-secondary)", borderLeft: "2px solid var(--violet-bright)", paddingLeft: "12px", margin: 0, fontStyle: "italic" }}>
                    "{cite.excerpt}"
                  </blockquote>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
