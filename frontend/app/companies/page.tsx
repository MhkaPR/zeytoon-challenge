import { Suspense } from "react";

import { getTranslations } from "next-intl/server";

import { CompanyCard } from "@/src/features/company/CompanyCard";
import { CompanyPagination } from "@/src/features/company/CompanyPagination";
import { CompanySearchBox } from "@/src/features/company/CompanySearchBox";
import { Card, Skeleton, Typography } from "@/src/features/ui/heroUi";
import { getCompaniesPage } from "@/src/lib/api/publicCatalog";
import { formatPersianNumber } from "@/src/lib/formatters/persian";

function first(value: string | string[] | undefined): string {
  return Array.isArray(value) ? (value[0] ?? "") : (value ?? "");
}

/** Provider directory, rendered and paginated on the server. */
export default function CompaniesPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string | string[]; page?: string | string[] }>;
}) {
  return (
    <Suspense fallback={<CompaniesLoading />}>
      <CompaniesContent searchParams={searchParams} />
    </Suspense>
  );
}

async function CompaniesContent({
  searchParams,
}: {
  searchParams: Promise<{ q?: string | string[]; page?: string | string[] }>;
}) {
  const ot = await getTranslations();
  const params = await searchParams;
  const query = first(params.q).trim();
  const requestedPage = Number(first(params.page));
  const page = Number.isFinite(requestedPage) && requestedPage > 0 ? requestedPage : 1;
  const companiesPage = await getCompaniesPage({ q: query, page, pageSize: 12 });

  return (
    <main className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-[32px] px-[16px] py-[48px] sm:px-[24px] md:px-[32px] md:py-[64px]">
      <header className="flex flex-col gap-[16px]">
        <div className="flex flex-col gap-[6px]">
          <Typography className="text-[32px] font-semibold sm:text-[40px]" type="h1">
            {ot("navCompanies")}
          </Typography>
          <Typography color="muted">{ot("companiesIntro")}</Typography>
        </div>
        <CompanySearchBox initialQuery={query} />
      </header>

      <div className="flex items-center justify-between gap-[12px]">
        <Typography color="muted" type="body-sm">
          {ot("companiesFoundCount", { count: formatPersianNumber(companiesPage.count) })}
        </Typography>
      </div>

      {companiesPage.companies.length ? (
        <div className="grid gap-[16px] sm:grid-cols-2 lg:grid-cols-3">
          {companiesPage.companies.map((company) => (
            <CompanyCard
              domain={company.domain}
              key={company.domain}
              name={company.company_name}
              planCount={company.plan_count}
            />
          ))}
        </div>
      ) : (
        <Card className="p-[24px]" variant="secondary">
          <Typography color="muted">
            {query ? ot("companiesSearchEmpty") : ot("companiesEmpty")}
          </Typography>
        </Card>
      )}

      <CompanyPagination
        page={companiesPage.page}
        query={query}
        totalPages={companiesPage.totalPages}
      />
    </main>
  );
}

function CompaniesLoading() {
  return (
    <main className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-[32px] px-[16px] py-[48px] sm:px-[24px] md:px-[32px] md:py-[64px]">
      <Skeleton className="h-[64px] w-full rounded-[var(--radius)]" />
      <Skeleton className="h-[320px] w-full rounded-[var(--radius)]" />
    </main>
  );
}
