"use client";

import { useTranslations } from "next-intl";
import { Typography } from "@heroui/react";

import type { ApprovalQueueEntry } from "@/src/lib/api/ops";
import { CompanyReviewCard } from "./CompanyReviewCard";

export function ApprovalQueue({
  entries,
  busyCompanyId,
  onDecision,
}: {
  entries: ApprovalQueueEntry[];
  busyCompanyId?: number | null;
  onDecision: (companyId: number, outcome: "approved" | "not_approved", note: string) => void;
}) {
  const ot = useTranslations("ops");
  if (entries.length === 0) {
    return (
      <Typography className="text-[14px] text-muted" role="status">
        {ot("approvalsEmpty")}
      </Typography>
    );
  }

  return (
    <div className="flex flex-col gap-[16px]">
      {entries.map((entry) => (
        <CompanyReviewCard
          busy={busyCompanyId === entry.company_id}
          entry={entry}
          key={entry.company_id}
          onDecision={onDecision}
        />
      ))}
    </div>
  );
}
