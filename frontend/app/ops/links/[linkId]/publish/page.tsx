"use client";

import { Button, Card, Chip, Skeleton, Typography } from "@heroui/react";
import { use, useState } from "react";

import { opsErrorMessage, useOpsData } from "@/src/features/ops/useOpsData";
import { getPlans, publishLink, setPlanIgnored } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";
import { getAccessToken } from "@/src/lib/session";

export default function OpsPublishPage({
  params,
}: {
  params: Promise<{ linkId: string }>;
}) {
  const { linkId } = use(params);
  const id = Number(linkId);
  const { data, loading, error, reload } = useOpsData(
    (token) => getPlans(token, id),
    String(id),
  );
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [accepted, setAccepted] = useState(false);
  const [savingPlanId, setSavingPlanId] = useState<number | null>(null);

  async function toggleIgnored(planId: number, ignored: boolean) {
    setSavingPlanId(planId);
    setFailure(null);
    try {
      await setPlanIgnored(getAccessToken(), id, planId, ignored);
      setAccepted(false);
      reload();
    } catch (issue) {
      setFailure(opsErrorMessage(issue));
    } finally {
      setSavingPlanId(null);
    }
  }

  async function acceptAndPublish() {
    setBusy(true);
    setFailure(null);
    try {
      await publishLink(getAccessToken(), id);
      setAccepted(true);
      reload();
    } catch (issue) {
      setFailure(opsErrorMessage(issue));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex flex-col gap-[20px]">
      <div className="flex flex-col gap-[4px]">
        <Typography className="text-[20px] font-semibold" type="h2">
          {opsStrings.qualityReviewTitle}
        </Typography>
        <Typography className="text-[13px] text-muted">
          {opsStrings.qualityReviewIntro}
        </Typography>
      </div>

      {accepted && (
        <Typography className="text-[13px] text-success" role="status">
          {opsStrings.qualityAccepted}
        </Typography>
      )}
      {failure && (
        <Typography className="text-[13px] text-danger" role="alert">
          {failure}
        </Typography>
      )}

      {loading ? (
        <Skeleton className="h-[220px] rounded-[var(--radius)]" />
      ) : error || !data ? (
        <Typography role="alert">{error ?? opsStrings.genericError}</Typography>
      ) : data.plans.length === 0 ? (
        <Typography className="text-[13px] text-muted" role="status">
          {opsStrings.noPlansForReview}
        </Typography>
      ) : (
        <>
          <Typography className="text-[13px] text-muted" role="status">
            {opsStrings.planIgnoreHint}
          </Typography>
          <div className="flex flex-col gap-[12px]">
            {data.plans.map((plan) => (
              <Card
                className={`flex flex-col gap-[12px] p-[18px] ${plan.ignored ? "opacity-60" : ""}`}
                key={plan.id}
                variant="default"
              >
                <div className="flex flex-wrap items-center justify-between gap-[8px]">
                  <Typography className="font-semibold" dir="ltr">
                    {plan.natural_key}
                  </Typography>
                  <div className="flex items-center gap-[8px]">
                    <Chip size="sm" variant="soft">
                      {plan.plan_type}
                    </Chip>
                    {plan.ignored && (
                      <Chip color="warning" size="sm" variant="soft">
                        {opsStrings.planIgnored}
                      </Chip>
                    )}
                    <Button
                      isDisabled={savingPlanId !== null || busy}
                      onPress={() => toggleIgnored(plan.id, !plan.ignored)}
                      size="sm"
                      variant={plan.ignored ? "secondary" : "tertiary"}
                    >
                      {savingPlanId === plan.id
                        ? opsStrings.saving
                        : plan.ignored
                          ? opsStrings.restorePlan
                          : opsStrings.ignorePlan}
                    </Button>
                  </div>
                </div>
                <dl className="grid gap-[8px] sm:grid-cols-2">
                  {Object.entries(plan.values).map(([key, value]) => (
                    <div className="rounded-[var(--radius)] bg-surface-secondary p-[10px]" key={key}>
                      <dt className="text-[11px] text-muted">{key}</dt>
                      <dd className="text-[13px]">{String(value ?? opsStrings.none)}</dd>
                    </div>
                  ))}
                </dl>
              </Card>
            ))}
          </div>
          <Button
            className="self-start"
            isDisabled={busy || accepted || data.plans.every((plan) => plan.ignored)}
            onPress={acceptAndPublish}
          >
            {busy ? opsStrings.publishing : opsStrings.acceptAndPublish}
          </Button>
        </>
      )}
    </main>
  );
}
