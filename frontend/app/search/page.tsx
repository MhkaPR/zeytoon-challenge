import { Typography } from "@heroui/react";
import { getTranslations } from "next-intl/server";

import { PlanCatalog } from "@/src/features/home/PlanCatalog";
import { SearchBox } from "@/src/features/home/SearchBox";
import { getPlansPage } from "@/src/lib/api/publicCatalog";

/** Search results, rendered on the server from the public catalog API. */
export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await searchParams;
  const raw = params.q;
  const query = Array.isArray(raw) ? (raw[0] ?? "") : (raw ?? "");
  const [ot, plansPage] = await Promise.all([
    getTranslations(),
    getPlansPage({ ...(query ? { q: query } : {}), page_size: "12" }),
  ]);

  return (
    <main className="mx-auto flex w-full max-w-[960px] flex-1 flex-col gap-[24px] px-[32px] py-[64px]">
      <Typography className="text-[32px] font-semibold" type="h1">{ot("searchTitle")}</Typography>
      <SearchBox initialQuery={query} />
      {query && <Typography color="muted">{ot("searchResultsFor", { query })}</Typography>}
      <PlanCatalog
        ariaLabel={ot("searchTitle")}
        baseParams={query ? { q: query } : {}}
        description={null}
        emptyState={
          <div className="rounded-[var(--radius)] border border-[var(--separator)] p-[24px]">
            <Typography className="font-semibold" type="h2">
              {query ? ot("searchNoPlansTitle") : ot("resultsEmptyTitle")}
            </Typography>
            <Typography color="muted">
              {query ? ot("searchNoPlansBody") : ot("searchEmptyHint")}
            </Typography>
          </div>
        }
        headerAction={null}
        key={query}
        plansPage={plansPage}
        searchParams={params}
        showServiceTabs={false}
        title={null}
      />
    </main>
  );
}
