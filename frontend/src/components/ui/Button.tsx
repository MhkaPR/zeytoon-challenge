import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost";
type Size = "md" | "sm";

const base =
  "inline-flex items-center justify-center gap-[8px] rounded-[var(--radius-standard)] " +
  "font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none " +
  "focus-visible:outline-none";

const variants: Record<Variant, string> = {
  // Primary Blue CTA (#1d4ed8 background, white text)
  primary:
    "bg-[var(--ds-blue-700)] text-white hover:bg-[var(--ds-blue-900)] shadow-[var(--ds-shadow-ring)]",
  // Primary White (shadow-bordered) secondary button — black text, blue accent on hover
  secondary:
    "bg-[var(--ds-white)] text-[var(--ds-ink)] shadow-[var(--ds-shadow-light-ring)] " +
    "hover:bg-[var(--ds-blue-900)] hover:text-white",
  // Text-only ghost button — black text, blue-tinted hover surface
  ghost: "bg-transparent text-[var(--ds-ink)] hover:bg-[var(--ds-blue-50)]",
};

const sizes: Record<Size, string> = {
  md: "px-[16px] py-[8px] text-[14px] leading-[1.43]",
  sm: "px-[10px] py-[6px] text-[14px] leading-none",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

/** Primary/secondary/ghost button following the DESIGN.md button system. */
export function Button({
  variant = "primary",
  size = "md",
  className = "",
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    />
  );
}
