import { useTranslations } from "next-intl";
import { Avatar, Typography } from "@heroui/react";
import NextLink from "next/link";

import type { RecentPublicCompany } from "@/src/lib/api/publicCatalog";
/** The three newest verified companies registered during the current month. */
export function RecentlyApproved({ companies }: { companies: RecentPublicCompany[] }) {
  const t = useTranslations("common");
  return (
    <section className="flex flex-col">
      <div className="flex flex-row items-end justify-between gap-[16px] py-2">
        <div className="flex flex-col gap-[8px]">
          <Typography className="text-[28px] font-semibold" type="h2">
            {t("recentlyApprovedTitle")}
          </Typography>
          <Typography className="max-w-[720px] leading-[1.8]" color="muted">
            {t("recentlyApprovedIntro")}
          </Typography>
        </div>
      </div>

      <hr className="mx-2" />
      {companies.length ? companies.map((company) => (
        <div className="flex flex-col" key={company.domain}>
          <NextLink
            className="flex w-full flex-row items-center gap-[12px] rounded-[var(--radius)] p-[12px] transition-colors hover:bg-default-50 focus-visible:outline-none"
            href={`/companies/${encodeURIComponent(company.domain)}`}
          >
            <Avatar>
              <Avatar.Fallback>{company.domain.substring(0, 2).toUpperCase()}</Avatar.Fallback>
            </Avatar>
            <div className="flex flex-1 flex-col gap-[2px]">
              <Typography className="font-medium">{company.company_name}</Typography>
              <Typography className="text-[12px]" color="muted" type="body">
                {company.domain}
              </Typography>
            </div>
            <Typography className="shrink-0 text-[12px]" color="muted" type="body-xs">
              {new Intl.DateTimeFormat("fa-IR", { month: "long", day: "numeric", timeZone: "Asia/Tehran" }).format(new Date(company.created_at))}
            </Typography>
          </NextLink>
          <hr className="mx-2" />
        </div>
      )) : (
        <Typography className="py-[20px]" color="muted" type="body-sm">
          در این ماه شرکتی برای نمایش اضافه نشده است.
        </Typography>
      )}
    </section>
  );
}
