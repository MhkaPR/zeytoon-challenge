import { useTranslations } from "next-intl";
import { Typography } from "@heroui/react";
import type { ReactNode } from "react";
import { AboutUs} from "@/src/features/home/AboutUs";
import { FaqSection } from "./FaqSection";
import { HomeFooter } from "./HomeFooter";
import { PlanCatalog } from "./PlanCatalog";
import { SuggestedPlans } from "./SuggestedPlans";
import { HomeCtas } from "./HomeCtas";
import { HowItWorks } from "./HowItWorks";
import { RecentlyApproved } from "./RecentlyApproved";
import { SearchBox } from "./SearchBox";
import type {
  PlansPage,
  PublicPlan,
  RecentPublicCompany,
} from "@/src/lib/api/publicCatalog";
import type { ClusterIntentExplanation } from "@/src/lib/api/intentExplanations";
import {SiteConfig} from "@/src/lib/config/siteConfig";

/**
 * The main page body: hero, search, catalog, homepage sections, and site footer.
 *
 * Published catalog records are fetched on the server and passed into the interactive
 * catalog client component.
 */
export function MainBody({
  brandLogo,
  plansPage,
  suggestedPlans,
  explanations,
  visitorId,
  recentCompanies,
  loading = false,
  searchParams,
  siteConfig,
}: {
  brandLogo?: ReactNode;
  plansPage: PlansPage;
  suggestedPlans: PublicPlan[];
  explanations?: ClusterIntentExplanation[];
  visitorId?: string;
  recentCompanies: RecentPublicCompany[];
  loading?: boolean;
  searchParams: Record<string, string | string[] | undefined>;
  siteConfig: SiteConfig;
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
          <HomeCtas />
        </section>

        <div className="flex w-full flex-col gap-[64px] py-[56px] text-start sm:gap-[80px] sm:py-[72px]">
          <SuggestedPlans
            explanations={explanations}
            loading={loading}
            plans={suggestedPlans}
            visitorId={visitorId}
          />
          <section className="scroll-mt-[80px]" id="pricing">
            <PlanCatalog
              key={JSON.stringify(searchParams)}
              loading={loading}
              plansPage={plansPage}
              searchParams={searchParams}
              visitorId={visitorId}
            />
          </section>
          <section className="scroll-mt-[80px]" id="providers">
            <RecentlyApproved companies={recentCompanies} loading={loading} />
          </section>
          <section className="scroll-mt-[80px]" id="steps">
            <HowItWorks />
          </section>
          <div className="rounded-[var(--radius)] bg-surface-secondary p-[20px] sm:p-[32px]">
            <AboutUs />
          </div>
          <FaqSection />
        </div>
      </div>

      <HomeFooter config={siteConfig}/>
    </>
  );
}
