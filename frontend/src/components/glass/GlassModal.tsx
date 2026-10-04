import { useEffect, type ReactNode } from "react";
import { X } from "lucide-react";

interface GlassModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
  maxWidth?: string;
  className?: string;
}

export function GlassModal({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  maxWidth = "780px",
  className = "",
}: GlassModalProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="glass-modal-backdrop" onClick={onClose} role="presentation">
      <div
        className={`glass-modal-card ${className}`}
        style={{ maxWidth }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="glass-modal-glow-edge" aria-hidden="true" />
        <div className="glass-modal-header">
          <div className="glass-modal-title-wrap">
            {title && <h3 className="glass-modal-title">{title}</h3>}
            {subtitle && <p className="glass-modal-subtitle">{subtitle}</p>}
          </div>
          <button
            type="button"
            className="glass-modal-close-btn"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </div>

        <div className="glass-modal-body">{children}</div>
      </div>
    </div>
  );
}
