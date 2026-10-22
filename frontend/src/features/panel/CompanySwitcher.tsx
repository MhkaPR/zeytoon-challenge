"use client";

import Link from "next/link";

import { Badge, Body } from "@/src/components/ui";
import type { SwitcherEntry } from "@/src/lib/api/companies";
import { strings } from "@/src/lib/i18n/strings";

function statusLabel(entry: SwitcherEntry): string {
  if (entry.verification_status === "verified") return strings.verifiedStatus;
  if (entry.verification_status === "rejected") return strings.rejectedStatus;
  return strings.pendingStatus;
}

/** Lets the user switch the active company; content follows the selected one (FR-022). */
export function CompanySwitcher({
  companies,
  activeId,
}: {
  companies: SwitcherEntry[];
  activeId?: number;
}) {
  return (
    <nav aria-label={strings.switchCompany} className="flex flex-wrap gap-[8px]">
      {companies.map((entry) => (
        <Link
          key={entry.id}
          href={`/panel/${entry.id}`}
          aria-current={entry.id === activeId ? "page" : undefined}
          className="flex items-center gap-[8px] rounded-[var(--radius-standard)] px-[12px] py-[8px] shadow-[var(--ds-shadow-light-ring)]"
        >
          <Body>{entry.company_name}</Body>
          <Badge>{statusLabel(entry)}</Badge>
        </Link>
      ))}
    </nav>
  );
}
