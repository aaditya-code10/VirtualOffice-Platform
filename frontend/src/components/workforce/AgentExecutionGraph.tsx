import {
  BrainCircuit,
  Crown,
  FileCheck2,
  Layers,
  Sparkles,
  Target,
  Gauge,
  Cpu,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import type { Agent } from "../../api";

interface AgentExecutionGraphProps {
  isExecuting?: boolean;
  activeStage?: "command" | "orchestrator" | "specialists" | "strategy" | "result";
  agents?: Agent[];
  verdict?: string | null;
}

export function AgentExecutionGraph({
  isExecuting = false,
  activeStage = isExecuting ? "specialists" : "result",
  agents = [],
  verdict = null,
}: AgentExecutionGraphProps) {
  const specialists = agents.filter((a) => !a.is_synthesizer);
  const synthesizer = agents.find((a) => a.is_synthesizer);

  return (
    <div className={`execution-graph-glass ${isExecuting ? "is-executing" : ""}`}>
      <div className="graph-header">
        <div className="graph-title-block">
          <BrainCircuit size={15} className="graph-title-icon" />
          <span className="graph-title">AUTONOMOUS MULTI-AGENT EXECUTION PIPELINE</span>
        </div>
        <div className="graph-status-badge">
          {isExecuting ? (
            <>
              <Loader2 size={12} className="spin text-violet" />
              <span className="text-violet">PARALLEL REASONING ACTIVE</span>
            </>
          ) : (
            <>
              <span className="status-dot-pulse" />
              <span>PIPELINE READY</span>
            </>
          )}
        </div>
      </div>

      {/* Visual Workflow Canvas */}
      <div className="graph-canvas">
        {/* Stage 1: User Command */}
        <div
          className={`graph-node node-command ${
            activeStage === "command" || isExecuting ? "active" : "ready"
          }`}
        >
          <div className="node-icon-box">
            <Sparkles size={16} />
          </div>
          <div className="node-text">
            <strong>01. Venture Intent</strong>
            <small>Directive & Proposal Context</small>
          </div>
        </div>

        {/* Dynamic Connecting Line 1 */}
        <div className="graph-connector">
          <div className="flow-line" />
          <div className="flow-pulse" />
        </div>

        {/* Stage 2: Orchestration Hub */}
        <div
          className={`graph-node node-orchestrator ${
            activeStage === "orchestrator" || isExecuting ? "active" : "ready"
          }`}
        >
          <div className="node-icon-box">
            <Layers size={16} />
          </div>
          <div className="node-text">
            <strong>02. Dynamic Router</strong>
            <small>Context Grounding Engine</small>
          </div>
        </div>

        {/* Dynamic Connecting Line 2 */}
        <div className="graph-connector">
          <div className="flow-line" />
          <div className="flow-pulse" />
        </div>

        {/* Stage 3: Specialist Pods (Parallel) */}
        <div className="graph-cluster node-specialists">
          <div className="cluster-label">
            <span>03. PARALLEL SPECIALIST EVALUATION</span>
          </div>
          <div className="specialist-nodes-grid">
            {(specialists.length > 0
              ? specialists
              : [
                  { key: "business_strategy", name: "Sarah Connor", department: "Strategy" },
                  { key: "market_research", name: "David Kim", department: "Market" },
                  { key: "finance", name: "Arthur Pendelton", department: "Finance" },
                  { key: "marketing", name: "Sophia Chen", department: "Growth" },
                ]
            ).map((sp) => (
              <div
                key={sp.key}
                className={`specialist-pill ${isExecuting ? "pulsing" : ""}`}
                title={`${sp.name} (${sp.department})`}
              >
                <span className="sp-icon">
                  {sp.key === "finance" ? (
                    <Gauge size={12} />
                  ) : sp.key === "marketing" ? (
                    <Sparkles size={12} />
                  ) : sp.key === "market_research" ? (
                    <Target size={12} />
                  ) : (
                    <Cpu size={12} />
                  )}
                </span>
                <span className="sp-name">{sp.name.split(" ")[0]}</span>
                <span className="sp-dept">{sp.department}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Dynamic Connecting Line 3 */}
        <div className="graph-connector">
          <div className="flow-line" />
          <div className="flow-pulse" />
        </div>

        {/* Stage 4: Managing Partner Synthesis */}
        <div
          className={`graph-node node-synthesizer ${
            activeStage === "strategy" || isExecuting ? "active" : "ready"
          }`}
        >
          <div className="node-icon-box crown">
            <Crown size={16} />
          </div>
          <div className="node-text">
            <strong>04. Executive Synthesis</strong>
            <small>{synthesizer?.name ?? "Jordan Blake"} · Verdict Arbiter</small>
          </div>
        </div>

        {/* Dynamic Connecting Line 4 */}
        <div className="graph-connector">
          <div className="flow-line" />
          <div className="flow-pulse" />
        </div>

        {/* Stage 5: Final Strategic Dossier */}
        <div
          className={`graph-node node-result ${
            verdict ? "has-verdict" : "ready"
          }`}
        >
          <div className="node-icon-box check">
            {verdict ? <CheckCircle2 size={16} /> : <FileCheck2 size={16} />}
          </div>
          <div className="node-text">
            <strong>05. Strategic Dossier</strong>
            <small>
              {verdict ? `Ruling: ${verdict}` : "Action Roadmap & Citations"}
            </small>
          </div>
        </div>
      </div>
    </div>
  );
}
