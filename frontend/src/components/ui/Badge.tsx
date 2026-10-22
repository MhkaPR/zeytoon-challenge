import type { HTMLAttributes } from "react";

/**
 * Pill badge: tinted olive background (#ecf2de), dark olive text (#4d6224), full-pill radius.
 * Pills are for badges/tags only — never primary action buttons.
 */
export function Badge({ className = "", ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={`inline-flex items-center rounded-full bg-[var(--ds-badge-bg)] px-[10px] py-[2px] text-[12px] font-medium leading-[1.33] text-[var(--ds-badge-text)] ${className}`}
      {...props}
    />
  );
}
