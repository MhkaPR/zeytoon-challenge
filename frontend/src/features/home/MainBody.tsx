"use client";

import { Typography } from "@heroui/react";
import type { ReactNode } from "react";
import { useState } from "react";

import { strings } from "@/src/lib/i18n/strings";
import { AboutTorb } from "./AboutTorb";
import { FaqSection } from "./FaqSection";
import { HomeCtas } from "./HomeCtas";
import { HomeFooter } from "./HomeFooter";
import { HomePlanCatalog } from "./HomePlanCatalog";
import { HowItWorks } from "./HowItWorks";
import { RankingCriteria } from "./RankingCriteria";
import { RecentlyApproved } from "./RecentlyApproved";
import { SearchBox } from "./SearchBox";
import { ServiceTypeChips } from "./ServiceTypeChips";
import { TopHosts } from "./TopHosts";
import type { ServiceTypeKey } from "./serviceTypes";

/**
 * The main page body (PAGES.yaml main page): hero brand logo, search box, the two browse
 * CTAs, service-type chips with the immediate filter box, then the explanatory homepage
 * sections — what Torb Host is, how it works, ranking criteria, top hosts, recently
 * approved, revenue model, FAQ — and the site footer.
 *
 * Results (plans and companies) render below the search field once a search runs; those
 * surfaces are owned by other features, so this shows the pending state.
 */
export function MainBody({ brandLogo }: { brandLogo?: ReactNode }) {
  const [serviceType, setServiceType] = useState<ServiceTypeKey>("host");

  return (
    <>
      <div className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col px-[24px] sm:px-[32px]">
        <section className="flex scroll-mt-[80px] flex-col items-center gap-[24px] py-[64px] text-center sm:gap-[32px] sm:py-[80px]">
          <div className="flex flex-col items-center gap-[12px]">
            {brandLogo ?? (
              <Typography className="font-semibold text-accent" type="body-sm">
                {strings.appName}
              </Typography>
            )}
            <Typography className="text-[12px] font-medium text-accent" type="body-xs">
              {strings.brandTagline}
            </Typography>
            <Typography
              className="max-w-[720px] text-[30px] font-semibold leading-[1.55] sm:text-[38px]"
              type="h1"
            >
              {strings.searchTitle}
            </Typography>
            <Typography className="max-w-[600px] text-[14px] leading-[1.9] sm:text-[16px]" color="muted">
              {strings.heroSubtitle}
            </Typography>
          </div>

          <div className="w-full max-w-[720px] rounded-[var(--radius)] border border-[var(--separator)] bg-surface p-[8px] shadow-overlay">
            <SearchBox />
          </div>
          <div className="w-full max-w-[520px]">
            <HomeCtas />
          </div>
        </section>

        <section
          aria-label={strings.serviceTypeLabel}
          className="scroll-mt-[80px] border-y border-[var(--separator)] py-[28px]"
        >
          <ServiceTypeChips value={serviceType} onChange={setServiceType} />
        </section>

        <div className="flex w-full flex-col gap-[64px] py-[56px] text-start sm:gap-[80px] sm:py-[72px]">
          <section className="scroll-mt-[80px]" id="pricing">
            <HomePlanCatalog />
          </section>
          <section className="scroll-mt-[80px]" id="providers">
            <TopHosts />
            <div className="mt-[40px]">
              <RecentlyApproved />
            </div>
          </section>
          <section className="scroll-mt-[80px]" id="steps">
            <HowItWorks />
          </section>
          <div className="flex flex-col gap-[64px] rounded-[var(--radius)] bg-surface-secondary p-[20px] sm:gap-[72px] sm:p-[32px]">
            <RankingCriteria />
            <AboutTorb />
          </div>
          <FaqSection />
        </div>
      </div>

      <HomeFooter />
    </>
  );
}
