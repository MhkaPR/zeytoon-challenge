"use client";

import { Card, Skeleton, Typography } from "@heroui/react";
import { useTranslations } from "next-intl";

import type { PublicPlan } from "@/src/lib/api/publicCatalog";
import type { ClusterIntentExplanation } from "@/src/lib/api/intentExplanations";

import { PlanRow } from "./planCatalog/PlanRow";

/**
 * Horizontally scrolling strip of the most relevant plans, drawn from the viewer's
 * interest clusters and ordered by recent activity on each cluster.
 */
export function SuggestedPlans({
  plans,
  explanations = [],
  visitorId,
  loading = false,
}: {
  plans: PublicPlan[];
  explanations?: ClusterIntentExplanation[];
  visitorId?: string;
  loading?: boolean;
}) {
  const ot = useTranslations();
  const rankByPlan = new Map(
    explanations
      .filter((item) => item.representative_plan_id != null)
      .map((item, index) => [item.representative_plan_id as number, index]),
  );
  const orderedPlans = [...plans].sort((a, b) => {
    const rankA = rankByPlan.get(a.id);
    const rankB = rankByPlan.get(b.id);
    if (rankA != null && rankB != null) return rankA - rankB;
    if (rankA != null) return -1;
    if (rankB != null) return 1;
    return 0;
  });
  const planById = new Map(plans.map((plan) => [plan.id, plan]));
  const visibleExplanations = explanations.filter(
    (explanation) => explanation.intent !== "exploring",
  );
  const hasExplanations = explanations.length > 0;
  if (loading) {
    return (
      <section className="flex flex-col gap-[18px]" id="suggested">
        <Typography className="text-[22px] font-semibold sm:text-[25px]" type="h2">
          {ot("suggestedTitle")}
        </Typography>
        <div aria-hidden className="flex gap-[16px] overflow-x-hidden">
          {Array.from({ length: 4 }, (_, index) => (
            <Card
              className="border border-[var(--separator)]"
              key={index}
              variant="default"
            >
              <Card.Content className="flex h-[220px] flex-col gap-[12px] p-[18px]">
                <Skeleton className="h-[20px] w-[70%] rounded-[6px]" />
                <Skeleton className="h-[32px] w-[55%] rounded-[6px]" />
                <Skeleton className="mt-auto h-[120px] w-full rounded-[8px]" />
              </Card.Content>
            </Card>
          ))}
        </div>
      </section>
    );
  }

  if (!plans.length) return null;
  if (hasExplanations && !visibleExplanations.length) return null;

  return (
    <section className="flex flex-col gap-[18px]" id="suggested">
      <div className="flex flex-col gap-[8px]">
        <Typography className="text-[22px] font-semibold sm:text-[25px]" type="h2">
          {ot("suggestedTitle")}
        </Typography>
        <Typography color="muted" type="body-sm">
          {ot("suggestedIntro")}
        </Typography>
      </div>
      {visibleExplanations.length ? (
        <div className="flex flex-col gap-[24px]">
          {visibleExplanations.map((explanation) => {
            const clusterPlans = explanation.plan_ids
              .map((planId) => planById.get(planId))
              .filter((plan): plan is PublicPlan => plan != null);
            if (!clusterPlans.length) return null;
            return (
              <section
                className="flex flex-col gap-[12px]"
                key={explanation.cluster_id}
              >
                <Typography
                  className="text-[13px] leading-[1.9]"
                  type="body-sm"
                >
                  {explanation.message}
                </Typography>
                <PlanRow
                  ariaLabel={explanation.message}
                  plans={clusterPlans}
                  visitorId={visitorId}
                />
              </section>
            );
          })}
        </div>
      ) : (
        <PlanRow
          ariaLabel={ot("suggestedTitle")}
          plans={orderedPlans}
          visitorId={visitorId}
        />
      )}
    </section>
  );
}
