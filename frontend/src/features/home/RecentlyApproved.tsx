import { useTranslations } from "next-intl";
import { Skeleton, Typography } from "@/src/features/ui/heroUi";
import NextLink from "next/link";

import { CompanyLogo } from "@/src/features/company/CompanyLogo";
import type { RecentPublicCompany } from "@/src/lib/api/publicCatalog";

const RECENT_COMPANY_DATE_FORMATTER = new Intl.DateTimeFormat("fa-IR-u-ca-gregory-nu-arabext", {
  day: "numeric",
  month: "numeric",
  timeZone: "Asia/Tehran",
});

/** The three newest verified companies registered during the current month. */
export function RecentlyApproved({
  companies,
  loading = false,
}: {
  companies: RecentPublicCompany[];
  loading?: boolean;
}) {
  const ot = useTranslations();
  return (
    <section className="flex flex-col">
      <div className="flex flex-row items-end justify-between gap-[16px] py-2">
        <div className="flex flex-col gap-[8px]">
          <Typography className="text-[28px] font-semibold" type="h2">
            {ot("recentlyApprovedTitle")}
          </Typography>
          <Typography className="max-w-[720px] leading-[1.8]" color="muted">
            {ot("recentlyApprovedIntro")}
          </Typography>
        </div>
      </div>

      <hr className="mx-2" />
      {loading ? (
        <div className="flex flex-col gap-[12px] py-[16px]" aria-hidden>
          {Array.from({ length: 3 }, (_, index) => (
            <Skeleton className="h-[64px] rounded-[var(--radius)]" key={index} />
          ))}
        </div>
      ) : companies.length ? companies.map((company) => (
        <div className="flex flex-col" key={company.domain}>
          <NextLink
            className="flex w-full flex-row items-center gap-[12px] rounded-[var(--radius)] p-[12px] transition-colors hover:bg-default-50 focus-visible:outline-none"
            href={`/companies/${encodeURIComponent(company.domain)}`}
          >
            <CompanyLogo
              domain={company.domain}
              name={company.company_name}
              size={40}
            />
            <div className="flex flex-1 flex-col gap-[2px]">
              <Typography className="font-medium">{company.company_name}</Typography>
              <Typography className="text-[12px]" color="muted" type="body">
                {company.domain}
              </Typography>
            </div>
            <Typography className="shrink-0 text-[12px]" color="muted" type="body-xs">
              {RECENT_COMPANY_DATE_FORMATTER.format(new Date(company.created_at))}
            </Typography>
          </NextLink>
          <hr className="mx-2" />
        </div>
      )) : (
        <Typography className="py-[20px]" color="muted" type="body-sm">
          {ot("recentlyApprovedEmpty")}
        </Typography>
      )}
    </section>
  );
}
