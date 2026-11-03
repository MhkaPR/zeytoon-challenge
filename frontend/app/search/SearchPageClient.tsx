"use client";

import { Card, Skeleton, Typography } from "@heroui/react";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { SearchBox } from "@/src/features/home/SearchBox";
import { displayField, getPublishedPlans, planName, type PublicPlan } from "@/src/lib/api/publicCatalog";
import {PlanCard} from "@/src/features/home/planCatalog/PlanCard";

/** Client-rendered search results; the query comes from the resolved URL search params. */
export function SearchPageClient({ query }: { query: string }) {
  const ot = useTranslations();
  const fieldLabels = ot.raw("fieldLabels") as Record<string, string>;
  const [plans, setPlans] = useState<PublicPlan[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    getPublishedPlans(query ? { q: query } : {})
      .then((nextPlans) => {
        if (active) setPlans(nextPlans);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [query]);

  return (
    <main className="mx-auto flex w-full max-w-[960px] flex-1 flex-col gap-[24px] px-[32px] py-[64px]">
      <Typography className="text-[32px] font-semibold" type="h1">{ot("searchTitle")}</Typography>
      <SearchBox />
      {query && <Typography color="muted">{ot("searchResultsFor", { query })}</Typography>}
      {loading ? <div className="grid gap-[14px] sm:grid-cols-2" aria-hidden>
        {Array.from({ length: 4 }, (_, index) => <Skeleton className="h-[190px] rounded-[var(--radius)]" key={index} />)}
      </div> : plans.length ? <div className="grid gap-[14px] sm:grid-cols-2">
        {plans.map((plan) => <PlanCard key={plan.id} plan={plan} />)}
      </div> : <Card variant="default"><Card.Header><Card.Title>{query ? ot("searchNoPlansTitle") : ot("resultsEmptyTitle")}</Card.Title><Card.Description>{query ? ot("searchNoPlansBody") : ot("searchEmptyHint")}</Card.Description></Card.Header></Card>}
    </main>
  );
}
