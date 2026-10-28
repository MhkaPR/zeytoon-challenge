"use client";

import { Button, Skeleton, Typography } from "@heroui/react";
import NextLink from "next/link";
import { useState } from "react";

import { ApprovalQueue } from "@/src/features/ops/approvals/ApprovalQueue";
import { opsErrorMessage, useOpsData } from "@/src/features/ops/useOpsData";
import { decideVerification, getApprovalQueue } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";
import { getAccessToken } from "@/src/lib/session";

interface DecisionOutcome {
  outcome: "approved" | "not_approved";
  siteId: number | null;
}

export default function OpsApprovalsPage() {
  const { data, loading, error, reload } = useOpsData(getApprovalQueue, "approvals");
  const [busyCompanyId, setBusyCompanyId] = useState<number | null>(null);
  const [results, setResults] = useState<Record<number, DecisionOutcome>>({});
  const [failure, setFailure] = useState<string | null>(null);

  async function decide(
    companyId: number,
    outcome: "approved" | "not_approved",
    note: string,
  ) {
    setBusyCompanyId(companyId);
    setFailure(null);
    try {
      const response = (await decideVerification(
        getAccessToken(),
        companyId,
        outcome,
        note,
      )) as { site?: { id: number } | null };
      setResults((prev) => ({
        ...prev,
        [companyId]: { outcome, siteId: response.site?.id ?? null },
      }));
      reload();
    } catch (err) {
      setFailure(opsErrorMessage(err));
    } finally {
      setBusyCompanyId(null);
    }
  }

  return (
    <main className="flex flex-col gap-[20px]">
      <div className="flex flex-col gap-[4px]">
        <Typography className="text-[20px] font-semibold" type="h2">
          {opsStrings.approvalsTitle}
        </Typography>
        <Typography className="text-[13px] text-muted">{opsStrings.approvalsIntro}</Typography>
      </div>

      {failure && (
        <Typography className="text-[13px] text-danger" role="alert">
          {failure}
        </Typography>
      )}

      {Object.entries(results).map(([companyId, result]) => (
        <Typography className="text-[13px] text-success" key={companyId} role="status">
          {result.outcome === "approved" ? opsStrings.approvedHint : opsStrings.rejectedHint}{" "}
          {result.siteId !== null && (
            <NextLink className="underline" href={`/ops/sites/${result.siteId}`}>
              {opsStrings.openSite}
            </NextLink>
          )}
        </Typography>
      ))}

      {loading ? (
        <Skeleton className="h-[220px] rounded-[var(--radius)]" />
      ) : error ? (
        <div className="flex flex-col items-start gap-[8px]">
          <Typography role="alert">{error}</Typography>
          <Button onPress={reload} size="sm" variant="secondary">
            {opsStrings.retry}
          </Button>
        </div>
      ) : (
        <ApprovalQueue
          busyCompanyId={busyCompanyId}
          entries={data?.results ?? []}
          onDecision={decide}
        />
      )}
    </main>
  );
}
