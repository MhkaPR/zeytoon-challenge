import type { HTMLAttributes } from "react";

/**
 * Typography primitives encoding the DESIGN.md hierarchy: three weights (400 read, 500
 * interact, 600 announce), negative tracking that scales with size, Geist Mono for
 * technical labels.
 */

type Tone = "ink" | "body" | "muted" | "accent";

const tones: Record<Tone, string> = {
  ink: "text-[var(--ds-ink)]",
  body: "text-[var(--ds-ink)]",
  muted: "text-[var(--ds-ink-muted)]",
  // Accent tone is reserved for links/active markers, never body copy.
  accent: "text-[var(--ds-blue-700)]",
};

export interface TextProps extends HTMLAttributes<HTMLElement> {
  tone?: Tone;
  as?: "p" | "span" | "div";
}

export function Body({ tone = "body", as = "p", className = "", ...props }: TextProps) {
  const Tag = as;
  return (
    <Tag
      className={`text-[16px] font-normal leading-[1.5] ${tones[tone]} ${className}`}
      {...props}
    />
  );
}

export function BodyLarge({ tone = "body", as = "p", className = "", ...props }: TextProps) {
  const Tag = as;
  return (
    <Tag
      className={`text-[20px] font-normal leading-[1.8] ${tones[tone]} ${className}`}
      {...props}
    />
  );
}

export function DisplayHero({ className = "", ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h1
      className={`text-[48px] font-semibold leading-[1.05] tracking-[-2.4px] text-[var(--ds-ink)] ${className}`}
      {...props}
    />
  );
}

export function SectionHeading({ className = "", ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h2
      className={`text-[40px] font-semibold leading-[1.2] tracking-[-2.4px] text-[var(--ds-ink)] ${className}`}
      {...props}
    />
  );
}

export function CardTitle({ className = "", ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={`text-[24px] font-semibold leading-[1.33] tracking-[-0.96px] text-[var(--ds-ink)] ${className}`}
      {...props}
    />
  );
}

/** Geist Mono uppercase technical label. */
export function MonoLabel({ className = "", ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={`font-mono text-[12px] font-medium uppercase leading-none text-[var(--ds-ink-muted)] ${className}`}
      {...props}
    />
  );
}
