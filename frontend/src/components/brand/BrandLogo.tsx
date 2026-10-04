import { Sparkles, BrainCircuit } from "lucide-react";

interface BrandLogoProps {
  size?: "sm" | "md" | "lg";
  showSubtitle?: boolean;
  className?: string;
  onClick?: () => void;
}

export function BrandLogo({
  size = "md",
  showSubtitle = true,
  className = "",
  onClick,
}: BrandLogoProps) {
  const iconSize = size === "lg" ? 28 : size === "sm" ? 18 : 22;

  return (
    <div
      className={`brand-logo-container size-${size} ${className}`}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      <div className="brand-symbol-wrapper">
        <div className="brand-halo" aria-hidden="true" />
        <div className="brand-symbol-glass">
          <BrainCircuit size={iconSize} className="brand-symbol-icon" />
          <Sparkles size={10} className="brand-sparkle-dot" />
        </div>
      </div>

      <div className="brand-text-block">
        <div className="brand-title">
          <span>Virtual</span>
          <span className="brand-title-accent">Office</span>
        </div>
        {showSubtitle && (
          <div className="brand-subtitle">
            <span className="pulse-dot" />
            <span>AI DIGITAL WORKFORCE</span>
          </div>
        )}
      </div>
    </div>
  );
}
