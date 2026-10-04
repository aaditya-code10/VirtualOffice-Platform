import { Bell, Sparkles } from "lucide-react";
import { useAuth } from "../../auth";
import type { SystemStatus } from "../../api";

interface TopBarProps {
  status: SystemStatus | null;
  onQuickAction?: () => void;
}

export function TopBar({ status }: TopBarProps) {
  const { user, company } = useAuth();

  const isOnline = Boolean(status?.llm_enabled);
  const engineModel = status?.llm_model || "Gemini 3.1 Flash Lite";

  return (
    <header className="glass-topbar">
      <div className="topbar-left">
        <div className="topbar-breadcrumb">
          <span className="crumb-app">VIRTUALOFFICE</span>
          <span className="crumb-divider">/</span>
          <span className="crumb-company">{company?.name || "ENTERPRISE WORKSPACE"}</span>
        </div>
      </div>

      <div className="topbar-right">
        {/* Softly pulsing AI Workforce Online indicator */}
        <div className={`topbar-ai-status ${isOnline ? "is-online" : "is-fallback"}`}>
          <span className="pulse-orb" />
          <span className="status-label">
            {isOnline ? "AI WORKFORCE ONLINE" : "LOCAL RULE ENGINE"}
          </span>
          <span className="engine-chip">
            <Sparkles size={11} className="engine-chip-icon" />
            {engineModel}
          </span>
        </div>

        {/* Quick notification button */}
        <button
          type="button"
          className="topbar-icon-btn"
          title="System notifications"
          aria-label="Notifications"
        >
          <Bell size={16} />
          <span className="notif-badge" />
        </button>

        {/* User profile avatar badge */}
        <div className="topbar-user-badge" title={`${user?.full_name} (${user?.email})`}>
          <div className="topbar-avatar">
            {user?.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}
          </div>
          <div className="topbar-user-text">
            <span className="name">{user?.full_name || "Operator"}</span>
            <span className="role">{user?.role || "OWNER"}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
