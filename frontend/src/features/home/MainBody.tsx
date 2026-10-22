"use client";

import type { ReactNode } from "react";
import { useState } from "react";

import { Body, BodyLarge, Card, MonoLabel } from "@/src/components/ui";
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
    <section className="flex flex-col items-center gap-[32px] text-center">
      {brandLogo ?? (
        <MonoLabel className="text-[var(--ds-olive-700)]">{strings.appName}</MonoLabel>
      )}
      <BodyLarge className="max-w-[640px]">{strings.searchTitle}</BodyLarge>

      <div className="w-full max-w-[720px]">
        <SearchBox />
      </div>

      <div className="w-full max-w-[960px] text-start">
        <ServiceTypeChips value={serviceType} onChange={setServiceType} />
      </div>

      <div className="w-full max-w-[960px] text-start">
        <FilterBox serviceType={serviceType} value={filters} onChange={setFilters} />
      </div>

      <Card variant="plain" className="w-full max-w-[960px] text-start">
        <MonoLabel>{strings.resultsTitle}</MonoLabel>
        <Body tone="muted" className="mt-[8px]">
          {strings.resultsPending}
        </Body>
      </Card>
    </section>
  );
}
