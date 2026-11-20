"use client";

import { useTranslations } from "next-intl";
import { buttonVariants, Button, Card, Chip, Skeleton, Typography } from "@heroui/react";
import { ArrowRight, RotateCcw } from "lucide-react";
import NextLink from "next/link";
import { useState } from "react";

import { CompanyForm } from "@/src/features/company/CompanyForm";
import { ApprovalQueue } from "@/src/features/ops/approvals/ApprovalQueue";
import { opsErrorMessage, useOpsData } from "@/src/features/ops/useOpsData";
import { decideVerification, getApprovalQueue, listSites, type Site } from "@/src/lib/api/ops";
import { getAccessToken } from "@/src/lib/session";

interface DecisionOutcome {
  outcome: "approved" | "not_approved";
  siteId: number | null;
}

export default function OpsApprovalsPage() {
  const ot = useTranslations();
  const { data, loading, error, reload } = useOpsData(getApprovalQueue, "approvals");
  const [busyCompanyId, setBusyCompanyId] = useState<number | null>(null);
  const [results, setResults] = useState<Record<number, DecisionOutcome>>({});
  const [failure, setFailure] = useState<string | null>(null);
  const [registrationNotice, setRegistrationNotice] = useState<string | null>(null);
  const sites = useOpsData(listSites, "sites");

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
      sites.reload();
    } catch (err) {
      setFailure(opsErrorMessage(err, ot));
    } finally {
      setBusyCompanyId(null);
    }
  }

  return (
    <main className="flex flex-col gap-[20px]">
      <section className="flex flex-col gap-[12px]">
        <Typography className="text-[20px] font-semibold" type="h2">
          {ot("registerForPipeline")}
        </Typography>
        <Typography className="text-[13px] text-muted">{ot("registerForPipelineHint")}</Typography>
        <CompanyForm
          onCreated={() => {
            setRegistrationNotice(ot("companyRegisteredForReview"));
            reload();
            sites.reload();
          }}
        />
        {registrationNotice && (
          <Typography className="text-[13px] text-success" role="status">
            {registrationNotice}
          </Typography>
        )}
      </section>

      <section className="flex flex-col gap-[12px]">
        <Typography className="text-[20px] font-semibold" type="h2">
          {ot("pipelineProgress")}
        </Typography>
        {sites.loading ? (
          <Skeleton className="h-[120px] rounded-[var(--radius)]" />
        ) : sites.error ? (
          <Typography role="alert">{sites.error}</Typography>
        ) : !sites.data?.results.length ? (
          <Typography className="text-[13px] text-muted">
            {ot("noPipelineSites")}
          </Typography>
        ) : (
          sites.data.results.map((site) => <PipelineSiteCard key={site.id} site={site} />)
        )}
      </section>

      <div className="flex flex-col gap-[4px]">
        <Typography className="text-[20px] font-semibold" type="h2">
          {ot("approvalsTitle")}
        </Typography>
        <Typography className="text-[13px] text-muted">{ot("approvalsIntro")}</Typography>
      </div>

      {failure && (
        <Typography className="text-[13px] text-danger" role="alert">
          {failure}
        </Typography>
      )}

      {Object.entries(results).map(([companyId, result]) => (
        <Typography className="text-[13px] text-success" key={companyId} role="status">
          {result.outcome === "approved" ? ot("approvedHint") : ot("opsRejectedHint")}{" "}
          {result.siteId !== null && (
            <NextLink
              className={buttonVariants({ size: "sm", variant: "secondary" })}
              href={`/ops/sites/${result.siteId}`}
            >
              <ArrowRight aria-hidden className="size-4" />
              {ot("openSite")}
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
            <RotateCcw aria-hidden className="size-4" />
            {ot("retry")}
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

function PipelineSiteCard({ site }: { site: Site & { links_count: number } }) {
  const ot = useTranslations();
  const stages = [
    "discovered",
    "captured",
    "extracted",
    "plans_extracted",
    "no_plans",
    "published",
  ];
  return (
    <Card className="flex flex-col gap-[12px] p-[16px]" variant="default">
      <div className="flex flex-wrap items-center justify-between gap-[8px]">
        <Typography className="font-semibold" dir="ltr">
          {site.domain}
        </Typography>
        <Chip size="sm" variant="soft">
          {site.links_count} {ot("linksCount")}
        </Chip>
      </div>
      {site.links_count ? (
        <div className="grid grid-cols-2 gap-[8px] sm:grid-cols-4">
          {stages.map((stage) => (
            <div
              className="rounded-[var(--radius)] bg-surface-secondary p-[8px] text-[12px]"
              key={stage}
            >
              {ot.raw("pipelineStage")[stage] ?? stage}: {site.stage_counts?.[stage] ?? 0}
            </div>
          ))}
        </div>
      ) : (
        <Typography className="text-[12px] text-muted">
          {ot("pipelineNoLinks")}
        </Typography>
      )}
      <NextLink
        className={buttonVariants({ size: "sm", variant: "secondary" })}
        href={`/ops/sites/${site.id}`}
      >
        <ArrowRight aria-hidden className="size-4" />
        {ot("openSite")}
      </NextLink>
    </Card>
  );
}
