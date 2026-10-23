"use client";

import { Chip } from "@heroui/react";
import { Building2, Check } from "lucide-react";
import NextLink from "next/link";

import type { SwitcherEntry } from "@/src/lib/api/companies";
import { strings } from "@/src/lib/i18n/strings";

import { verificationColor, verificationLabel } from "./status";

/**
 * Company switcher. Renders as a horizontal, scrollable row of selectable cards so the panel
 * keeps the same layout on mobile and desktop; the active company is clearly marked and the
 * content below always reflects the selected one (FR-022).
 */
export function CompanySwitcher({
  companies,
  activeId,
}: {
  companies: SwitcherEntry[];
  activeId?: number;
}) {
  if (companies.length === 0) return null;

  return (
    <nav aria-label={strings.switchCompany} className="w-full">
      <ul className="-mx-[4px] flex snap-x snap-mandatory gap-[12px] overflow-x-auto px-[4px] pb-[4px]">
        {companies.map((entry) => {
          const active = entry.id === activeId;
          return (
            <li key={entry.id} className="snap-start">
              <NextLink
                aria-current={active ? "true" : undefined}
                href={`/panel/${entry.id}`}
                className={`flex min-w-[220px] flex-col gap-[10px] rounded-[var(--radius)] bg-surface p-[16px] shadow-surface transition-all hover:shadow-overlay mt-2 ${
                  active ? "ring-2 ring-accent" : "ring-1 ring-border"
                }`}
              >
                <div className="flex items-center gap-[8px]">
                  <span
                    aria-hidden
                    className={`flex size-[32px] shrink-0 items-center justify-center rounded-full ${
                      active ? "bg-accent text-accent-foreground" : "bg-surface-secondary text-muted"
                    }`}
                  >
                    {active ? <Check className="size-4" /> : <Building2 className="size-4" />}
                  </span>
                  <span className="truncate text-[15px] font-semibold">{entry.company_name}</span>
                </div>
                <Chip color={verificationColor(entry.verification_status)} size="sm" variant="soft">
                  {verificationLabel(entry.verification_status)}
                </Chip>
              </NextLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
