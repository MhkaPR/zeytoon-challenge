"use client";

import { Typography } from "@heroui/react";
import type { ReactNode } from "react";
import { useState } from "react";

import { strings } from "@/src/lib/i18n/strings";
import { AboutTorb } from "./AboutTorb";
import { FaqSection } from "./FaqSection";
import { HomeCtas } from "./HomeCtas";
import { HomeFooter } from "./HomeFooter";
import { HowItWorks } from "./HowItWorks";
import { RecentlyApproved } from "./RecentlyApproved";
import { SearchBox } from "./SearchBox";
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
      <div className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-[80px] px-[32px] py-[80px]">
        {/* Hero: brand logo, headline, search box, and the two browse CTAs. */}
        <section className="flex flex-col items-center gap-[40px] text-center">
          <div className="flex flex-col items-center gap-[16px]">
            {brandLogo ?? (
              <Typography className="font-semibold text-accent" type="body-xs">
                {strings.appName}
              </Typography>
            )}
            <Typography
              className="max-w-[640px] text-[28px] font-semibold leading-[1.5] sm:text-[32px]"
              type="h1"
            >
              {strings.searchTitle}
            </Typography>
            <Typography className="max-w-[560px] text-[16px] leading-[1.8]" color="muted">
              {strings.heroSubtitle}
            </Typography>
          </div>

          <div className="w-full max-w-[720px]">
            <SearchBox />
          </div>
          <HomeCtas />
        </section>

        <div className="flex w-full flex-col gap-[80px] text-start">
          <AboutTorb />
          <HowItWorks />
          <RecentlyApproved />
          <FaqSection />
        </div>
      </div>

      <HomeFooter />
    </>
  );
}
