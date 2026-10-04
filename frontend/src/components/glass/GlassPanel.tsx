import type { HTMLAttributes, ReactNode } from "react";

interface GlassPanelProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  variant?: "default" | "glow" | "elevated" | "subtle";
  className?: string;
}

export function GlassPanel({
  children,
  variant = "default",
  className = "",
  ...props
}: GlassPanelProps) {
  return (
    <div className={`glass-panel glass-panel--${variant} ${className}`} {...props}>
      {children}
    </div>
  );
}
