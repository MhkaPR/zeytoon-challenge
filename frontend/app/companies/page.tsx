"use client";

import { Card, Skeleton, Typography } from "@heroui/react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useEffect, useState } from "react";

import { getPublishedPlans, planName, type PublicPlan } from "@/src/lib/api/publicCatalog";

/** Provider directory: a client-rendered SPA route backed by the public catalog API. */
export default function CompaniesPage() {
  const ot = useTranslations();
  const [plans, setPlans] = useState<PublicPlan[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    getPublishedPlans()
      .then((nextPlans) => {
        if (active) setPlans(nextPlans);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const providers = [...new Map(plans.map((plan) => [plan.domain, plan])).values()];
  return (
    <main className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-[32px] px-[32px] py-[64px]">
      <div><Typography className="text-[40px] font-semibold" type="h1">{ot("navCompanies")}</Typography><Typography color="muted">{ot("companiesIntro")}</Typography></div>
      {loading ? <div className="grid gap-[16px] sm:grid-cols-2 lg:grid-cols-3" aria-hidden>
        {Array.from({ length: 6 }, (_, index) => <Skeleton className="h-[150px] rounded-[var(--radius)]" key={index} />)}
      </div> : providers.length ? <div className="grid gap-[16px] sm:grid-cols-2 lg:grid-cols-3">
        {providers.map((provider) => {
          const providerPlans = plans.filter((plan) => plan.domain === provider.domain);
          return <Link href={`/companies/${encodeURIComponent(provider.domain)}`} key={provider.domain}>
            <Card className="flex h-full flex-col gap-[10px] p-[20px]"><Typography className="font-semibold" type="h2">{provider.company_name}</Typography><Typography color="muted" type="body-sm">{provider.domain}</Typography><Typography type="body-sm">{ot("plansPublishedCount", { count: providerPlans.length })}</Typography><Typography color="muted" type="body-xs">{planName(providerPlans[0])}</Typography></Card>
          </Link>;
        })}
      </div> : <Card className="p-[24px]" variant="secondary"><Typography color="muted">{ot("companiesEmpty")}</Typography></Card>}
    </main>
  );
}
