"use client";

import { useTranslations } from "next-intl";
import { Button, Card, Chip, Skeleton, Typography } from "@heroui/react";
import { EyeOff, RotateCcw, Send } from "lucide-react";
import { use, useState } from "react";

import { LinkStageNav } from "@/src/features/ops/pipeline/LinkStageNav";
import { opsErrorMessage, useOpsData } from "@/src/features/ops/useOpsData";
import { getPlans, publishLink, setPlanIgnored } from "@/src/lib/api/ops";
import { getAccessToken } from "@/src/lib/session";

export default function OpsPublishPage({
  params,
}: {
  params: Promise<{ linkId: string }>;
}) {
  const ot = useTranslations();
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
      setFailure(opsErrorMessage(issue, ot));
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
      setFailure(opsErrorMessage(issue, ot));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex flex-col gap-[20px]">
      <div className="flex flex-col gap-[4px]">
        <Typography className="text-[20px] font-semibold" type="h2">
          {ot("qualityReviewTitle")}
        </Typography>
      </div>

      {accepted && (
        <Typography className="text-[13px] text-success" role="status">
          {ot("qualityAccepted")}
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
        <Typography role="alert">{error ?? ot("genericError")}</Typography>
      ) : data.plans.length === 0 ? (
        <Typography className="text-[13px] text-muted" role="status">
          {ot("noPlansForReview")}
        </Typography>
      ) : (
        <>
          <Typography className="text-[13px] text-muted" role="status">
            {ot("planIgnoreHint")}
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
                        {ot("planIgnored")}
                      </Chip>
                    )}
                    <Button
                      isDisabled={savingPlanId !== null || busy}
                      onPress={() => toggleIgnored(plan.id, !plan.ignored)}
                      size="sm"
                      variant={plan.ignored ? "secondary" : "tertiary"}
                    >
                      {plan.ignored ? (
                        <RotateCcw aria-hidden className="size-4" />
                      ) : (
                        <EyeOff aria-hidden className="size-4" />
                      )}
                      {savingPlanId === plan.id
                        ? ot("saving")
                        : plan.ignored
                          ? ot("restorePlan")
                          : ot("ignorePlan")}
                    </Button>
                  </div>
                </div>
                <dl className="grid gap-[8px] sm:grid-cols-2">
                  {Object.entries(plan.values).flatMap(([key, value]) => {
                    if (key === "other") return [];
                    const displayValue = Array.isArray(value)
                      ? value.join(", ")
                      : value && typeof value === "object"
                        ? JSON.stringify(value)
                        : String(value ?? ot("none"));
                    return [
                      <div className="rounded-[var(--radius)] bg-surface-secondary p-[10px]" key={key}>
                        <dt className="text-[11px] text-muted">{key}</dt>
                        <dd className="text-[13px]">{displayValue}</dd>
                      </div>,
                    ];
                  })}
                </dl>
              </Card>
            ))}
          </div>
          <Button
            className="self-start"
            isDisabled={busy || accepted || data.plans.every((plan) => plan.ignored)}
            onPress={acceptAndPublish}
          >
            <Send aria-hidden className="size-4" />
            {busy ? ot("publishing") : ot("acceptAndPublish")}
          </Button>
        </>
      )}
    </main>
  );
}
