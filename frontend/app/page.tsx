
import { Suspense } from "react";
import { MainBody } from "@/src/features/home/MainBody";
import { getPlansPage, getRecentCompanies } from "@/src/lib/api/publicCatalog";
import {Skeleton} from "@heroui/react";
import {getSiteConfig} from "@/src/lib/config/getSiteConfig";
import { visitorId } from "@/src/lib/visitor";

type SearchParams = Record<string, string | string[] | undefined>;

export default function MainPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>; // Next.js 15
}) {
  return (
    <main className="flex flex-1 flex-col">
      <Suspense fallback={<Skeleton />}>
        <MainContent searchParams={searchParams} />
      </Suspense>
    </main>
  );
}

async function MainContent({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const siteConfig = await getSiteConfig();
  const requestedPageSize = Array.isArray(params.page_size)
    ? params.page_size[0]
    : params.page_size;
  const vid = await visitorId();
  const [plansPage, recentCompanies] = await Promise.all([
    getPlansPage({
      ...params,
      page_size: requestedPageSize ?? String(siteConfig.catalog.defaultPageSize),
    }, { visitorId: vid }),
    getRecentCompanies(),
  ]);


  return (
    <MainBody
      plansPage={plansPage}
      visitorId={vid}
      recentCompanies={recentCompanies}
      searchParams={params}
      siteConfig={siteConfig}
    />
  );
}
