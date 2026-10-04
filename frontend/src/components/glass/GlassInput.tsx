import { forwardRef, type InputHTMLAttributes, type ReactNode } from "react";

interface GlassInputProps extends InputHTMLAttributes<HTMLInputElement> {
  icon?: ReactNode;
  endAdornment?: ReactNode;
  containerClassName?: string;
}

export const GlassInput = forwardRef<HTMLInputElement, GlassInputProps>(
  ({ icon, endAdornment, containerClassName = "", className = "", ...props }, ref) => {
    return (
      <div className={`glass-input-wrapper ${containerClassName}`}>
        {icon && <span className="glass-input-icon">{icon}</span>}
        <input ref={ref} className={`glass-input ${icon ? "has-icon" : ""} ${className}`} {...props} />
        {endAdornment && <div className="glass-input-adornment">{endAdornment}</div>}
      </div>
    );
  },
);

GlassInput.displayName = "GlassInput";
