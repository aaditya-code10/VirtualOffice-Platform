import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  BrainCircuit,
  FileText,
  Lightbulb,
  Loader2,
  Paperclip,
  Sparkles,
  X,
  TrendingUp,
  ShieldAlert,
  CheckCircle2,
  ArrowUpRight,
  Database,
  Layers,
  Crown,
  Award,
} from "lucide-react";

import {
  ApiError,
  api,
  type Agent,
  type DocumentRecord,
  type WorkOrder,
  type WorkOrderSummary,
} from "../api";
import { Empty, ErrorBanner, Layout } from "../components/Layout";
import { WorkOrderModal } from "../components/WorkOrderModal";
import { AgentExecutionGraph } from "../components/workforce/AgentExecutionGraph";
import { AgentCard } from "../components/workforce/AgentCard";

const CATEGORIES = [
  { id: "General Venture", label: "General Business", emoji: "💡" },
  { id: "Education & Coaching", label: "Education & Tuition", emoji: "🎓" },
  { id: "Food & Dining", label: "Food & Dining", emoji: "🍱" },
  { id: "Tech & SaaS", label: "Tech & Software", emoji: "💻" },
  { id: "Retail & E-commerce", label: "Retail & E-comm", emoji: "🛍️" },
  { id: "Healthcare & Services", label: "Health & Care", emoji: "🏥" },
  { id: "Offline & Real Estate", label: "Offline Services", emoji: "🏢" },
];

const QUICK_PROMPTS = [
  {
    label: "Identify biggest business risk",
    prompt: "Identify the single biggest risk facing our business model, cash-flow, and competitive moat, and recommend mitigation steps.",
  },
  {
    label: "Evaluate break-even & unit economics",
    prompt: "Stress-test our unit economics, pricing model, gross margins, and calculate realistic break-even timeline under conservative projections.",
  },
  {
    label: "Design 30-day go-to-market plan",
    prompt: "Create an aggressive 30-day go-to-market strategy focusing on high-ROI organic and paid customer acquisition channels.",
  },
  {
    label: "Analyze sales & conversion bottlenecks",
    prompt: "Analyze our sales conversion funnel, customer friction points, and provide immediate fixes to lift monthly recurring revenue.",
  },
];

function VerdictBadge({ verdict }: { verdict: string | null }) {
  if (!verdict) return <span className="verdict-badge pending">PENDING</span>;
  const v = verdict.toUpperCase();
  if (v.includes("NO-GO") || v.includes("NOGO")) {
    return (
      <span className="verdict-badge nogo">
        <ShieldAlert size={12} /> NO-GO
      </span>
    );
  }
  if (v.includes("PIVOT")) {
    return (
      <span className="verdict-badge pivot">
        <TrendingUp size={12} /> PIVOT
      </span>
    );
  }
  if (v.includes("GO")) {
    return (
      <span className="verdict-badge go">
        <CheckCircle2 size={12} /> GO
      </span>
    );
  }
  return <span className="verdict-badge pending">{verdict.slice(0, 15)}</span>;
}

export default function CommandCenter() {
  const navigate = useNavigate();
  const location = useLocation();
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [agents, setAgents] = useState<Agent[]>([]);
  const [recent, setRecent] = useState<WorkOrderSummary[]>([]);
  const [docs, setDocs] = useState<DocumentRecord[]>([]);
  const [command, setCommand] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("General Venture");
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [statusMessage, setStatusMessage] = useState("");
  const [running, setRunning] = useState(false);
  const [selected, setSelected] = useState<WorkOrder | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [a, wo, d] = await Promise.all([
        api.getAgents(),
        api.getWorkOrders({ limit: 10 }),
        api.getDocuments(),
      ]);
      setAgents(a);
      setRecent(wo);
      setDocs(d);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load command center.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get("focus") === "true" && inputRef.current) {
      inputRef.current.focus();
    }
    const qPrompt = params.get("prompt");
    if (qPrompt) {
      setCommand(qPrompt);
    }
  }, [location.search]);

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setAttachedFile(file);
      setError(null);
    }
  }

  function removeFile() {
    setAttachedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  async function run(target?: string) {
    const text = (target ?? command).trim();
    if (!text && !attachedFile) return;
    if (running) return;

    setRunning(true);
    setError(null);
    try {
      let documentId: string | undefined = undefined;

      if (attachedFile) {
        setStatusMessage(`Ingesting & parsing "${attachedFile.name}" via PDF chunking engine...`);
        const uploadedDoc = await api.uploadDocument(attachedFile);
        documentId = uploadedDoc.id;
      }

      setStatusMessage("5 AI Advisors executing parallel deep reasoning (~15-20s)...");
      const effectiveCommand =
        text ||
        (attachedFile
          ? `Analyze the attached business proposal (${attachedFile.name}) for our ${selectedCategory} venture in detail. Evaluate business model viability, target market, unit economics, faculty/staffing, risks, and strategic next steps.`
          : `Comprehensive strategic evaluation of ${selectedCategory} business venture.`);

      const order = await api.createWorkOrder(effectiveCommand, undefined, {
        document_id: documentId,
        category: selectedCategory,
      });

      setSelected(order);
      setCommand("");
      setAttachedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Analysis could not be completed.");
    } finally {
      setRunning(false);
      setStatusMessage("");
    }
  }

  function fillPrompt(p: string) {
    setCommand(p);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }

  return (
    <Layout>
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      <div style={{ display: "flex", flexDirection: "column", gap: "24px", width: "100%", maxWidth: "100%", minWidth: 0, boxSizing: "border-box" }}>
        {/* ── 1. Liquid Glass Central Command Hero ───────────────────────── */}
        <section className="apex-hero">
          <div className="apex-eyebrow">
            <Sparkles size={13} />
            AUTONOMOUS AI EXECUTIVE WORKFORCE · LIQUID GLASS OS
          </div>

          <h1 className="apex-hero-title">
            Ask anything about your business.
          </h1>

          <p className="apex-hero-subtitle">
            The right specialists analyze the problem together. Deploy five specialized AI advisors in parallel
            to evaluate strategy, analyze market demand, stress-test finances, and deliver synthesized executive verdicts.
          </p>

          {/* Sector Selector */}
          <div className="sector-bar">
            <span className="sector-label">SECTOR:</span>
            {CATEGORIES.map((cat) => {
              const isSelected = selectedCategory === cat.id;
              return (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => setSelectedCategory(cat.id)}
                  disabled={running}
                  className={`sector-pill ${isSelected ? "active" : ""}`}
                >
                  <span>{cat.emoji}</span>
                  <span>{cat.label}</span>
                </button>
              );
            })}
          </div>

          {/* Central Glass Composer */}
          <div className="apex-composer">
            <div className="composer-input-row">
              <input
                ref={inputRef}
                value={command}
                placeholder={
                  attachedFile
                    ? `Optional focus notes for "${attachedFile.name}" (or press Execute for full dossier)…`
                    : `e.g. Evaluate launch strategy for our premium Mumbai corporate tiffin service with ₹5 lakh budget…`
                }
                onChange={(e) => setCommand(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && run()}
                disabled={running}
              />

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt,.md"
                onChange={handleFileSelect}
                style={{ display: "none" }}
              />
            </div>

            {/* Bottom Toolbar */}
            <div className="composer-toolbar">
              <div className="toolbar-left">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={running}
                  className={`btn-attach ${attachedFile ? "has-file" : ""}`}
                  title="Attach Business Proposal PDF or Document"
                >
                  <Paperclip size={14} />
                  <span>{attachedFile ? "Change Proposal PDF" : "Attach Proposal PDF"}</span>
                </button>

                {attachedFile && (
                  <div className="attached-pdf-pill">
                    <FileText size={14} style={{ color: "var(--violet-bright)" }} />
                    <span style={{ fontWeight: 600, maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {attachedFile.name}
                    </span>
                    <span className="grounded-tag">✓ GROUNDED IN PDF</span>
                    <button
                      type="button"
                      onClick={removeFile}
                      disabled={running}
                      title="Remove attached file"
                      style={{
                        background: "none",
                        border: "none",
                        color: "var(--text-muted)",
                        cursor: "pointer",
                        display: "flex",
                        padding: "2px",
                      }}
                    >
                      <X size={14} />
                    </button>
                  </div>
                )}
              </div>

              <div className="toolbar-right">
                <span className="key-hint">↵ Enter</span>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => run()}
                  disabled={running || (!command.trim() && !attachedFile)}
                >
                  {running ? (
                    <>
                      <Loader2 size={15} className="spin" />
                      <span>Executing Deep Reasoning…</span>
                    </>
                  ) : (
                    <>
                      <span>{attachedFile ? "Execute with Proposal PDF" : "Execute Deep Assessment"}</span>
                      <ArrowRight size={14} />
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Running progress alert */}
          {running && (
            <div className="analysis-progress-bar">
              <Loader2 size={16} className="spin" />
              <span>{statusMessage || "Multi-agent evaluation executing in parallel (~15-20s)…"}</span>
            </div>
          )}

          {/* Quick Prompts Glass Pills */}
          <div className="example-row">
            <span className="example-label">QUICK PROMPTS:</span>
            {QUICK_PROMPTS.map((item) => (
              <button
                key={item.label}
                type="button"
                className="example-chip"
                onClick={() => fillPrompt(item.prompt)}
                disabled={running}
              >
                <Sparkles size={12} style={{ color: "var(--soft-blue)" }} />
                <span>{item.label}</span>
              </button>
            ))}
          </div>
        </section>

        {/* ── 2. Multi-Agent Reasoning Execution Pipeline ────────────────── */}
        <AgentExecutionGraph
          isExecuting={running}
          agents={agents}
          verdict={recent[0]?.recommendation}
        />

        {/* ── 3. Executive Telemetry Strip ───────────────────────────────── */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">
              <Layers size={20} />
            </div>
            <div className="stat-copy">
              <span>Completed Evaluations</span>
              <strong>{recent.length}</strong>
              <small>Strategic executive dossiers</small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon" style={{ color: "var(--warning)" }}>
              <Crown size={20} />
            </div>
            <div className="stat-copy">
              <span>Autonomous C-Suite</span>
              <strong style={{ color: "var(--warning)" }}>{agents.length || 5}</strong>
              <small>Specialized AI advisors</small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon" style={{ color: "var(--success)" }}>
              <Award size={20} />
            </div>
            <div className="stat-copy">
              <span>Advisory Disciplines</span>
              <strong style={{ color: "var(--success)" }}>4</strong>
              <small>Strategy, Market, Finance, Growth</small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon" style={{ color: "var(--electric-blue)" }}>
              <Database size={20} />
            </div>
            <div className="stat-copy">
              <span>Knowledge Grounding</span>
              <strong style={{ color: "var(--electric-blue)" }}>{docs.length}</strong>
              <small>Indexed PDF & business docs</small>
            </div>
          </div>
        </div>

        {/* ── 4. Split: Recent Evaluations & AI Advisory Board Grid ──────── */}
        <div className="dashboard-split">
          {/* Recent Evaluations Panel */}
          <div className="panel">
            <div className="panel-head">
              <h2>Recent Strategic Evaluations</h2>
              <button
                type="button"
                className="link-btn"
                onClick={() => navigate("/work-orders")}
              >
                <span>View All Work Orders</span>
                <ArrowUpRight size={13} />
              </button>
            </div>

            {recent.length === 0 ? (
              <Empty
                icon={<Lightbulb size={24} />}
                text="No venture analyses yet. Begin by entering an idea or attaching a business proposal."
              />
            ) : (
              <div className="orders-list">
                {recent.slice(0, 6).map((order) => (
                  <div key={order.id} className="order-row">
                    <div className="order-symbol">
                      <BrainCircuit size={16} />
                    </div>

                    <div className="order-copy">
                      <strong>
                        {order.command.length > 70 ? order.command.slice(0, 70) + "…" : order.command}
                      </strong>
                      <span>
                        {new Date(order.created_at).toLocaleDateString("en-IN", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "6px" }}>
                      <VerdictBadge verdict={order.recommendation} />
                      <button
                        type="button"
                        onClick={() =>
                          api
                            .getWorkOrder(order.id)
                            .then(setSelected)
                            .catch(() => undefined)
                        }
                        style={{
                          background: "none",
                          border: "none",
                          color: "var(--violet-bright)",
                          fontSize: "12px",
                          fontWeight: 600,
                          cursor: "pointer",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "4px",
                        }}
                      >
                        <span>View Dossier</span>
                        <ArrowRight size={11} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* AI Executive Advisory Workforce Roster */}
          <div className="panel">
            <div className="panel-head">
              <h2>AI Workforce Roster</h2>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--success)", fontWeight: 700 }}>
                ● {agents.length || 5} AGENTS ONLINE
              </span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {agents.map((agent) => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  onClick={() => navigate(`/agents/${agent.key}`)}
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {selected && <WorkOrderModal order={selected} onClose={() => setSelected(null)} />}
    </Layout>
  );
}
