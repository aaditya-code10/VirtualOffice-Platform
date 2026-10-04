import type { ButtonHTMLAttributes, ReactNode } from "react";

interface GlassButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost" | "danger" | "success";
  size?: "sm" | "md" | "lg";
  icon?: ReactNode;
  loading?: boolean;
  className?: string;
}

export function GlassButton({
  children,
  variant = "primary",
  size = "md",
  icon,
  loading = false,
  className = "",
  disabled,
  ...props
}: GlassButtonProps) {
  const classes = [
    "glass-btn",
    `glass-btn--${variant}`,
    `glass-btn--${size}`,
    loading ? "glass-btn--loading" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button className={classes} disabled={disabled || loading} {...props}>
      <span className="glass-btn-reflection" aria-hidden="true" />
      {icon && <span className="glass-btn-icon">{icon}</span>}
      <span className="glass-btn-content">{children}</span>
    </button>
  );
}
