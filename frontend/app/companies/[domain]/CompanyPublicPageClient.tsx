"use client";

import { Card, Skeleton, Typography } from "@heroui/react";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { displayField, getPublishedPlans, planName, type PublicPlan } from "@/src/lib/api/publicCatalog";
import {PlanCard} from "@/src/features/home/planCatalog/PlanCard";

/** Client-rendered company comparison; the domain comes from the resolved route params. */
export function CompanyPublicPageClient({ domain }: { domain: string }) {
  const ot = useTranslations();
  const fieldLabels = ot.raw("fieldLabels") as Record<string, string>;
  const [plans, setPlans] = useState<PublicPlan[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    getPublishedPlans({ domain })
      .then((nextPlans) => {
        if (active) setPlans(nextPlans);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [domain]);

  const companyName = plans[0]?.company_name ?? domain;
  return (
    <main className="mx-auto flex w-full max-w-[1100px] flex-1 flex-col gap-[24px] px-[24px] py-[56px] sm:px-[32px]">
      <div><Typography className="text-[34px] font-semibold" type="h1">{companyName}</Typography><Typography color="muted">{domain}</Typography></div>
      <Typography className="text-[22px] font-semibold" type="h2">{ot("publishedPlansTitle")}</Typography>
      {loading ? <div className="grid gap-[14px] sm:grid-cols-2 lg:grid-cols-3" aria-hidden>
        {Array.from({ length: 3 }, (_, index) => <Skeleton className="h-[190px] rounded-[var(--radius)]" key={index} />)}
      </div> : plans.length ? <div className="grid gap-[14px] sm:grid-cols-2 lg:grid-cols-3">{plans.map((plan) => <PlanCard key={plan.id} plan={plan}/>)}</div> : <Card variant="secondary" className="p-[24px]"><Typography color="muted">{ot("companyNoPlans")}</Typography></Card>}
    </main>
  );
}
