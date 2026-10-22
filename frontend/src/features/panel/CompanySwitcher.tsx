"use client";

import { Chip, Link, Typography } from "@heroui/react";
import NextLink from "next/link";

import type { SwitcherEntry } from "@/src/lib/api/companies";
import { strings } from "@/src/lib/i18n/strings";

function statusLabel(entry: SwitcherEntry): string {
  if (entry.verification_status === "verified") return strings.verifiedStatus;
  if (entry.verification_status === "rejected") return strings.rejectedStatus;
  return strings.pendingStatus;
}

function statusColor(entry: SwitcherEntry) {
  if (entry.verification_status === "verified") return "success" as const;
  if (entry.verification_status === "rejected") return "danger" as const;
  return "warning" as const;
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
          aria-current={entry.id === activeId ? "page" : undefined}
          className={`flex items-center gap-[8px] rounded-full px-[14px] py-[8px] transition-colors ${
            entry.id === activeId
              ? "bg-accent text-accent-foreground shadow-surface"
              : "bg-surface shadow-surface hover:bg-surface-secondary"
          }`}
          href={`/panel/${entry.id}`}
          render={({ ref, ...domProps }) => (
            <NextLink {...domProps} ref={ref as React.Ref<HTMLAnchorElement>} href={`/panel/${entry.id}`} />
          )}
        >
          <Typography className="font-medium">{entry.company_name}</Typography>
          <Chip color={statusColor(entry)}>{statusLabel(entry)}</Chip>
        </Link>
      ))}
    </nav>
  );
}
