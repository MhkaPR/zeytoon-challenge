import type { SelectHTMLAttributes } from "react";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  hint?: string;
  options: SelectOption[];
  placeholder?: string;
}

/**
 * Native select styled with the shadow-as-border technique (no CSS border) so it matches
 * the input system while remaining keyboard- and RTL-friendly.
 */
export function Select({
  label,
  hint,
  options,
  placeholder,
  className = "",
  id,
  ...props
}: SelectProps) {
  return (
    <label className="flex flex-col gap-[6px] text-[14px] font-medium text-[var(--ds-ink)]">
      {label}
      <select
        id={id}
        className={`rounded-[var(--radius-standard)] bg-[var(--ds-white)] px-[12px] py-[8px] text-start text-[14px] leading-[1.5] text-[var(--ds-ink)] shadow-[var(--ds-shadow-ring)] outline-none focus-visible:shadow-[var(--ds-shadow-light-ring)] ${className}`}
        {...props}
      >
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {hint && <span className="text-[12px] font-normal text-[var(--ds-ink-muted)]">{hint}</span>}
    </label>
  );
}
