import type { HTMLAttributes } from "react";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** ``featured`` uses the full multi-layer shadow stack; ``plain`` uses the subtle stack. */
  variant?: "plain" | "featured";
}

/**
 * Card with the shadow-as-border technique (no CSS border), radius 8px, white surface.
 * The inner ``#eff6ff`` ring in the featured stack is what gives the card its inner glow.
 */
export function Card({ variant = "plain", className = "", ...props }: CardProps) {
  const shadow = variant === "featured" ? "shadow-[var(--ds-shadow-card)]" : "shadow-[var(--ds-shadow-subtle)]";
  return (
    <div
      className={`bg-[var(--ds-white)] text-start rounded-[var(--radius-comfortable)] ${shadow} p-[16px] ${className}`}
      {...props}
    />
  );
}
