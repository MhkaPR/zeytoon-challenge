import { Card, Typography } from "@heroui/react";
import { getTranslations } from "next-intl/server";

import { SearchBox } from "@/src/features/home/SearchBox";
import { PlanCard } from "@/src/features/home/planCatalog/PlanCard";
import { getPublishedPlans } from "@/src/lib/api/publicCatalog";

/** Search results, rendered on the server from the public catalog API. */
export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const raw = (await searchParams).q;
  const query = Array.isArray(raw) ? (raw[0] ?? "") : (raw ?? "");
  const [ot, plans] = await Promise.all([
    getTranslations(),
    getPublishedPlans(query ? { q: query } : {}),
  ]);

  return (
    <main className="mx-auto flex w-full max-w-[960px] flex-1 flex-col gap-[24px] px-[32px] py-[64px]">
      <Typography className="text-[32px] font-semibold" type="h1">{ot("searchTitle")}</Typography>
      <SearchBox />
      {query && <Typography color="muted">{ot("searchResultsFor", { query })}</Typography>}
      {plans.length ? (
        <div className="grid gap-[14px] sm:grid-cols-2">
          {plans.map((plan) => <PlanCard key={plan.id} plan={plan} />)}
        </div>
      ) : (
        <Card variant="default">
          <Card.Header>
            <Card.Title>{query ? ot("searchNoPlansTitle") : ot("resultsEmptyTitle")}</Card.Title>
            <Card.Description>{query ? ot("searchNoPlansBody") : ot("searchEmptyHint")}</Card.Description>
          </Card.Header>
        </Card>
      )}
    </main>
  );
}
