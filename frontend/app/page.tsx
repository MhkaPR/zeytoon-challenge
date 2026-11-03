
import { Suspense } from "react";
import { MainBody } from "@/src/features/home/MainBody";
import {
  getPublishedPlans,
  getRecentCompanies,
} from "@/src/lib/api/publicCatalog";
import {Skeleton} from "@heroui/react";
import {getSiteConfig} from "@/src/lib/config/siteConfig";

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

  const normalized = Object.fromEntries(
    Object.entries(params).map(([k, v]) => [
      k,
      Array.isArray(v) ? v[0] : v ?? "",
    ]),
  ) as Record<string, string>;

  const [plans, recentCompanies, siteConfig] = await Promise.all([
    getPublishedPlans(normalized),
    getRecentCompanies(),
    getSiteConfig()
  ]);


  return <MainBody plans={plans} recentCompanies={recentCompanies} siteConfig={siteConfig}/>;
}