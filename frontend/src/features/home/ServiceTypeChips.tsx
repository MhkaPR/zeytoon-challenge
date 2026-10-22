"use client";

import { MonoLabel } from "@/src/components/ui";
import { strings } from "@/src/lib/i18n/strings";
import { SERVICE_TYPES, type ServiceTypeKey } from "./serviceTypes";

/**
 * A horizontal row of service-type chips that filter results fast. Exactly one chip is
 * active at a time; the active chip drives which resources the filter box shows
 * (PAGES.yaml "chips").
 */
export function ServiceTypeChips({
  value,
  onChange,
}: {
  value: ServiceTypeKey;
  onChange: (next: ServiceTypeKey) => void;
}) {
  return (
    <div className="flex flex-col gap-[8px]">
      <MonoLabel>{strings.serviceTypeLabel}</MonoLabel>
      <div role="group" aria-label={strings.serviceTypeLabel} className="flex flex-wrap gap-[8px]">
        {SERVICE_TYPES.map((type) => {
          const active = type.key === value;
          return (
            <button
              key={type.key}
              type="button"
              aria-pressed={active}
              onClick={() => onChange(type.key)}
              className={`rounded-full px-[14px] py-[6px] text-[14px] font-medium transition-colors ${
                active
                  ? "bg-[var(--ds-olive-700)] text-white"
                  : "bg-[var(--ds-badge-bg)] text-[var(--ds-badge-text)] hover:bg-[var(--ds-olive-200)]"
              }`}
            >
              {type.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
