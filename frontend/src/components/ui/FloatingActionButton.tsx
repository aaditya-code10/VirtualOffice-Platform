import { useState } from "react";
import { Sparkles, ArrowUp, X } from "lucide-react";

interface FloatingActionButtonProps {
  onTrigger?: () => void;
  quickPrompts?: string[];
  onSelectPrompt?: (prompt: string) => void;
}

export function FloatingActionButton({
  onTrigger,
  quickPrompts = [
    "Assess our business model strengths & weaknesses",
    "Identify top 3 cash-flow & break-even risks",
    "Recommend customer acquisition launch strategy",
  ],
  onSelectPrompt,
}: FloatingActionButtonProps) {
  const [open, setOpen] = useState(false);

  const handlePromptClick = (p: string) => {
    onSelectPrompt?.(p);
    setOpen(false);
  };

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="fab-container">
      {open && (
        <div className="fab-menu glass-panel glass-panel--glow">
          <div className="fab-menu-header">
            <span className="fab-menu-title">⚡ QUICK ADVISORY ASSISTANT</span>
            <button
              type="button"
              className="fab-menu-close"
              onClick={() => setOpen(false)}
              aria-label="Close menu"
            >
              <X size={14} />
            </button>
          </div>
          <div className="fab-menu-list">
            {quickPrompts.map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                className="fab-prompt-pill"
                onClick={() => handlePromptClick(prompt)}
              >
                <Sparkles size={12} className="fab-pill-icon" />
                <span>{prompt}</span>
              </button>
            ))}
          </div>
          <div className="fab-menu-footer">
            <button type="button" className="fab-scroll-top-btn" onClick={scrollToTop}>
              <ArrowUp size={12} /> Scroll to top
            </button>
          </div>
        </div>
      )}

      <button
        type="button"
        className={`fab-button ${open ? "is-open" : ""}`}
        onClick={() => {
          if (onTrigger && !open) onTrigger();
          setOpen((v) => !v);
        }}
        aria-label="AI Advisory Actions"
        title="AI Digital Workforce Quick Actions"
      >
        <span className="fab-halo" aria-hidden="true" />
        <Sparkles size={18} className="fab-icon" />
      </button>
    </div>
  );
}
