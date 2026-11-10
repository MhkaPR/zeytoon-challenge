"use client";

import { Card, Skeleton, Typography } from "@heroui/react";
import { useTranslations } from "next-intl";

import type { PublicPlan } from "@/src/lib/api/publicCatalog";
import type { ClusterExplanation } from "@/src/lib/api/explanations";

import { PlanCard } from "./planCatalog/PlanCard";

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
  explanations?: ClusterExplanation[];
  visitorId?: string;
  loading?: boolean;
}) {
  const ot = useTranslations();
  const reasonByPlan = new Map(
    explanations
      .filter((item) => item.representative_plan_id != null)
      .map((item) => [item.representative_plan_id as number, item.reasons]),
  );
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
      <ul
        aria-label={ot("suggestedTitle")}
        className="-mx-[24px] flex snap-x snap-mandatory gap-[16px] overflow-x-auto px-[24px] pb-[6px] sm:mx-0 sm:px-0"
      >
        {orderedPlans.map((plan) => (
          <li
            className="shrink-0 snap-start list-none"
            key={plan.id}
          >
            <PlanCard
              explanation={reasonByPlan.get(plan.id)}
              plan={plan}
              visitorId={visitorId}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}
