"use client";

import { Card, Typography } from "@heroui/react";
import type { ReactNode } from "react";
import { useState } from "react";

import { strings } from "@/src/lib/i18n/strings";
import { FilterBox, EMPTY_FILTERS, type FilterState } from "./FilterBox";
import { SearchBox } from "./SearchBox";
import { ServiceTypeChips } from "./ServiceTypeChips";
import type { ServiceTypeKey } from "./serviceTypes";

/**
 * The main page body: brand logo, search box, service-type chips, and the immediate filter
 * box. Results (plans and companies) render below the search field once a search runs;
 * those surfaces are owned by other features, so this shows the pending state.
 */
export function MainBody({ brandLogo }: { brandLogo?: ReactNode }) {
  const [serviceType, setServiceType] = useState<ServiceTypeKey>("host");
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS);

  return (
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
    </section>
  );
}
