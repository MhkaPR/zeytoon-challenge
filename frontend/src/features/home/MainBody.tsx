import { useTranslations } from "next-intl";
import { Typography } from "@heroui/react";
import type { ReactNode } from "react";

import { AboutTorb } from "./AboutTorb";
import { FaqSection } from "./FaqSection";
import { HomeCtas } from "./HomeCtas";
import { HomeFooter } from "./HomeFooter";
import { HomePlanCatalog } from "./HomePlanCatalog";
import { HowItWorks } from "./HowItWorks";
import { RankingCriteria } from "./RankingCriteria";
import { RecentlyApproved } from "./RecentlyApproved";
import { SearchBox } from "./SearchBox";
import type { PublicPlan, RecentPublicCompany } from "@/src/lib/api/publicCatalog";
import {useSiteConfig} from "@/src/features/site/SiteConfigProvider";
import {SiteConfig} from "@/src/lib/config/siteConfig";

/**
 * The main page body: hero, search, catalog, homepage sections, and site footer.
 *
 * Published catalog records are fetched by the client-rendered home route.
 */
export function MainBody({
  brandLogo,
  plans,
  recentCompanies,
  loading = false,
  siteConfig
}: {
  brandLogo?: ReactNode;
  plans: PublicPlan[];
  recentCompanies: RecentPublicCompany[];
  loading?: boolean;
  siteConfig: SiteConfig
}) {
  const ot = useTranslations();
  return (
    <>
      <div className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col px-[24px] sm:px-[32px]">
        <section className="flex scroll-mt-[80px] flex-col items-center gap-[24px] py-[64px] text-center sm:gap-[32px] sm:py-[80px]">
          <div className="flex flex-col items-center gap-[12px]">
            {brandLogo ?? (
              <Typography className="font-semibold text-accent" type="body-sm">
                {ot("appName")}
              </Typography>
            )}
            <Typography className="text-[12px] font-medium text-accent" type="body-xs">
              {ot("brandTagline")}
            </Typography>
            <Typography
              className="max-w-[720px] text-[30px] font-semibold leading-[1.55] sm:text-[38px]"
              type="h1"
            >
              {ot("searchTitle")}
            </Typography>
            <Typography className="max-w-[600px] text-[14px] leading-[1.9] sm:text-[16px]" color="muted">
              {ot("heroSubtitle")}
            </Typography>
          </div>

          <div className="w-full max-w-[720px] rounded-[var(--radius)] border border-[var(--separator)] bg-surface p-[8px] shadow-overlay">
            <SearchBox />
          </div>
        </section>

        <div className="flex w-full flex-col gap-[64px] py-[56px] text-start sm:gap-[80px] sm:py-[72px]">
          <section className="scroll-mt-[80px]" id="pricing">
            <HomePlanCatalog loading={loading} plans={plans} />
          </section>
          <section className="scroll-mt-[80px]" id="providers">
            <RecentlyApproved companies={recentCompanies} loading={loading} />
          </section>
          <section className="scroll-mt-[80px]" id="steps">
            <HowItWorks />
          </section>
          <div className="rounded-[var(--radius)] bg-surface-secondary p-[20px] sm:p-[32px]">
            <AboutTorb />
          </div>
          <FaqSection />
        </div>
      </div>

      <HomeFooter config={siteConfig}/>
    </>
  );
}
