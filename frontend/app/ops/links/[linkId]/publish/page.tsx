"use client";

import { useTranslations } from "next-intl";
import { Button, Card, Chip, Skeleton, Typography } from "@heroui/react";
import { use, useState } from "react";

import { opsErrorMessage, useOpsData } from "@/src/features/ops/useOpsData";
import { getPlans, publishLink, setPlanIgnored } from "@/src/lib/api/ops";
import { getAccessToken } from "@/src/lib/session";

function flattenOther(value: unknown, parentKey = "", depth = 0, fallbackLabel = ""): Array<{ key: string; value: string }> {
  if (depth > 5 || value == null) return [];
  if (typeof value === "string") {
    const trimmed = value.trim();
    if ((trimmed.startsWith("[") && trimmed.endsWith("]")) || (trimmed.startsWith("{") && trimmed.endsWith("}"))) {
      try {
        return flattenOther(JSON.parse(trimmed), parentKey, depth + 1);
      } catch {
        const pairs = [...trimmed.matchAll(/\{\s*'((?:\\.|[^'])*)'\s*:\s*'((?:\\.|[^'])*)'\s*\}/g)];
        if (pairs.length) {
          const decode = (text: string) => text
            .replace(/\\u([\da-fA-F]{4})/g, (_, code: string) => String.fromCharCode(parseInt(code, 16)))
            .replace(/\\'/g, "'")
            .replace(/\\\\/g, "\\");
          return pairs.flatMap(([, rawKey, rawValue]) =>
            flattenOther({ [decode(rawKey)]: decode(rawValue) }, parentKey, depth + 1),
          );
        }
      }
    }
    return trimmed ? [{ key: parentKey || fallbackLabel, value: trimmed }] : [];
  }
  if (Array.isArray(value)) {
    return value.flatMap((entry) => flattenOther(entry, parentKey, depth + 1));
  }
  if (typeof value !== "object") return [];

  const record = value as Record<string, unknown>;
  if ("key" in record || "value" in record) {
    const key = String(record.key ?? parentKey ?? fallbackLabel);
    if (key === "values.other") return flattenOther(record.value, "", depth + 1);
    if (record.value === "" || record.value == null) return [{ key, value: "" }];
    return flattenOther(record.value, key, depth + 1);
  }
  return Object.entries(record).flatMap(([key, nested]) => {
    if (key === "values.other" || key === "other") return flattenOther(nested, "", depth + 1);
    if (nested === "" || nested == null) return [{ key, value: "" }];
    return flattenOther(nested, key, depth + 1);
  });
}

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
        <Typography className="text-[13px] text-muted">
          {ot("qualityReviewIntro")}
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
                    if (key === "other" && Array.isArray(value)) {
                      const details = flattenOther(value);
                      if (!details.length) return [];
                      return [
                        <div className="rounded-[var(--radius)] bg-surface-secondary p-[12px]" key="other">
                          <dt className="mb-[8px] text-[12px] font-medium text-muted">{ot("otherAttributes")}</dt>
                          <dd>
                            <ul className="flex flex-col gap-[6px]">
                              {details.map((item, index) => (
                                <li className="text-[13px] leading-6" key={`other-${index}`}>
                                  {item.value ? `${item.key}: ${item.value}` : item.key}
                                </li>
                              ))}
                            </ul>
                          </dd>
                        </div>,
                      ];
                    }
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
            {busy ? ot("publishing") : ot("acceptAndPublish")}
          </Button>
        </>
      )}
    </main>
  );
}
