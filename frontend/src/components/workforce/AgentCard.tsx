import {
  Brain,
  Cpu,
  Gauge,
  Sparkles,
  Target,
  Crown,
  ArrowRight,
} from "lucide-react";
import type { Agent } from "../../api";

interface AgentCardProps {
  agent: Agent;
  onClick?: () => void;
  isProcessing?: boolean;
}

export function AgentCard({ agent, onClick, isProcessing = false }: AgentCardProps) {
  const getIcon = () => {
    if (agent.is_synthesizer) return <Crown size={20} />;
    switch (agent.key) {
      case "business_strategy":
        return <Cpu size={20} />;
      case "market_research":
        return <Target size={20} />;
      case "finance":
        return <Gauge size={20} />;
      case "marketing":
        return <Sparkles size={20} />;
      default:
        return <Brain size={20} />;
    }
  };

  const getStatusColor = () => {
    if (isProcessing || agent.status === "working") return "working";
    if (agent.status === "online") return "online";
    if (agent.status === "blocked") return "error";
    return "idle";
  };

  const statusType = getStatusColor();

  return (
    <div
      className={`agent-glass-card agent-card--${statusType} ${agent.is_synthesizer ? "agent-card--synthesizer" : ""}`}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      <div className="agent-glass-halo" aria-hidden="true" />

      {/* Card Header: Department & Live Status */}
      <div className="agent-card-header">
        <span className="agent-department-badge">
          {agent.department.toUpperCase()}
        </span>
        <div className={`agent-status-indicator status-${statusType}`}>
          <span className="status-ping" />
          <span className="status-label">
            {isProcessing ? "ANALYZING" : agent.status.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Identity block */}
      <div className="agent-identity">
        <div className="agent-avatar-orb">
          {getIcon()}
          {agent.is_synthesizer && <span className="master-star">★</span>}
        </div>
        <div className="agent-title-group">
          <h4 className="agent-name">{agent.name}</h4>
          <p className="agent-role">{agent.role}</p>
        </div>
      </div>

      {/* Current Focus / Remit */}
      <div className="agent-focus-box">
        <div className="focus-label">FOCUS REMIT</div>
        <div className="focus-text">{agent.focus}</div>
      </div>

      {/* Health Meter */}
      <div className="agent-health-strip">
        <div className="health-labels">
          <span>OPERATIONAL COGNITION</span>
          <span className="health-number">{agent.health}%</span>
        </div>
        <div className="health-track">
          <div
            className="health-bar"
            style={{ width: `${agent.health}%` }}
          />
        </div>
      </div>

      {/* Action footer */}
      {onClick && (
        <div className="agent-card-footer">
          <span className="footer-action-text">Open Specialist Desk</span>
          <ArrowRight size={13} className="footer-arrow" />
        </div>
      )}
    </div>
  );
}
