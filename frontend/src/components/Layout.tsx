/** Application shell: Liquid Glass Sidebar, TopBar, Animated Background, and Page Frame. */
import { useEffect, useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { X } from "lucide-react";

import { api, type SystemStatus } from "../api";
import { AnimatedBackground } from "./background/AnimatedBackground";
import { GlassSidebar } from "./navigation/GlassSidebar";
import { TopBar } from "./navigation/TopBar";
import { FloatingActionButton } from "./ui/FloatingActionButton";

export function Layout({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    api.systemStatus().then(setStatus).catch(() => setStatus(null));
  }, []);

  function handleNewAssessment() {
    if (location.pathname === "/") {
      const inputEl = document.querySelector<HTMLInputElement>(".composer-input-row input");
      if (inputEl) {
        inputEl.focus();
        inputEl.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    } else {
      navigate("/?focus=true");
    }
  }

  function handleFabSelectPrompt(prompt: string) {
    if (location.pathname === "/") {
      const inputEl = document.querySelector<HTMLInputElement>(".composer-input-row input");
      if (inputEl) {
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
          window.HTMLInputElement.prototype,
          "value"
        )?.set;
        if (nativeInputValueSetter) {
          nativeInputValueSetter.call(inputEl, prompt);
          inputEl.dispatchEvent(new Event("input", { bubbles: true }));
        }
        inputEl.focus();
        inputEl.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    } else {
      navigate(`/?focus=true&prompt=${encodeURIComponent(prompt)}`);
    }
  }

  return (
    <div className="app-shell">
      {/* 1. Global Atmospheric Ambient Canvas */}
      <AnimatedBackground />

      {/* 2. Floating Liquid Glass Sidebar */}
      <GlassSidebar onNewAssessment={handleNewAssessment} />

      {/* 3. Main Workspace Shell Frame */}
      <div className="main-shell">
        <TopBar status={status} onQuickAction={handleNewAssessment} />
        <main className="content-shell">{children}</main>
      </div>

      {/* 4. Floating Action Assistant Button */}
      <FloatingActionButton
        onTrigger={handleNewAssessment}
        onSelectPrompt={handleFabSelectPrompt}
      />
    </div>
  );
}

export function Header({
  title = "AI Executive Advisory Board",
  subtitle = "Stress-test and evaluate your enterprise venture with specialized AI agents.",
  actions,
}: {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      {actions && <div style={{ marginLeft: "auto" }}>{actions}</div>}
    </div>
  );
}

export function Empty({
  icon,
  text,
  action,
}: {
  icon: ReactNode;
  text: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-panel glass-panel">
      <div>
        <div
          style={{
            display: "grid",
            placeItems: "center",
            marginBottom: "12px",
            color: "var(--violet-bright)",
          }}
        >
          {icon}
        </div>
        <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>{text}</p>
        {action && <div style={{ marginTop: "16px" }}>{action}</div>}
      </div>
    </div>
  );
}

export function ErrorBanner({
  message,
  onDismiss,
}: {
  message: string;
  onDismiss?: () => void;
}) {
  return (
    <div className="error-banner" role="alert">
      <span>{message}</span>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss alert"
          style={{
            background: "none",
            border: "none",
            color: "inherit",
            cursor: "pointer",
            display: "grid",
            placeItems: "center",
            padding: "2px",
          }}
        >
          <X size={15} />
        </button>
      )}
    </div>
  );
}

export function Spinner({ label = "Executing autonomous reasoning…" }: { label?: string }) {
  return (
    <div className="spinner-row" style={{ display: "flex", alignItems: "center", gap: "10px", color: "var(--violet-bright)" }}>
      <span className="spinner" aria-hidden />
      <span>{label}</span>
    </div>
  );
}
