import type { InputHTMLAttributes } from "react";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
}

/**
 * Text input using the shadow-as-border technique instead of a CSS border, with the
 * consistent blue focus ring.
 */
export function Input({ label, hint, className = "", id, ...props }: InputProps) {
  return (
    <label className="flex flex-col gap-[6px] text-[14px] font-medium text-[var(--ds-ink)]">
      {label}
      <input
        id={id}
        className={`rounded-[var(--radius-standard)] bg-[var(--ds-white)] px-[12px] py-[8px] text-start text-[16px] leading-[1.5] text-[var(--ds-ink)] shadow-[var(--ds-shadow-ring)] outline-none placeholder:text-[var(--ds-ink-muted)] focus-visible:shadow-[var(--ds-shadow-light-ring)] ${className}`}
        {...props}
      />
      {hint && <span className="text-[12px] font-normal text-[var(--ds-ink-muted)]">{hint}</span>}
    </label>
  );
}
