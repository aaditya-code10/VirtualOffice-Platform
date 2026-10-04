import type { HTMLAttributes, ReactNode } from "react";

interface GlassCardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  interactive?: boolean;
  active?: boolean;
  glow?: "violet" | "blue" | "success" | "none";
  className?: string;
}

export function GlassCard({
  children,
  interactive = false,
  active = false,
  glow = "none",
  className = "",
  ...props
}: GlassCardProps) {
  const classes = [
    "glass-card",
    interactive ? "glass-card--interactive" : "",
    active ? "glass-card--active" : "",
    glow !== "none" ? `glass-card--glow-${glow}` : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={classes} {...props}>
      <div className="glass-card-inner-highlight" aria-hidden="true" />
      {children}
    </div>
  );
}
