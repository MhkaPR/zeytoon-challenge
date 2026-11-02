"use client";

import { useTranslations } from "next-intl";
import { Label, SearchField, ToggleButton, ToggleButtonGroup } from "@heroui/react";
import { useState } from "react";

import { ResultsList } from "./ResultsList";
import { SERVICE_TYPES, suggest, type ServiceKey } from "./data";

/**
 * The main-page search surface: a sticky search field with the service-type chips directly
 * below it and a live suggestion list under the field. The detailed filter panel lives on
 * the home page (``FilterBox``).
 */
export function SearchExperience() {
  const t = useTranslations("common");
  const [query, setQuery] = useState("");
  const [service, setService] = useState<ServiceKey>("host");

  const results = suggest(query, service);
  const hasQuery = Boolean(query.trim());

  return (
    <div className="flex w-full flex-col gap-[16px]">
      {/* Sticky search + chips stack: chips sit directly below the sticky search field. */}
      <div className="sticky top-[64px] z-20 -mx-[16px] bg-surface px-[16px] pb-[12px] pt-[12px] md:-mx-[32px] md:px-[32px]">
        <SearchField aria-label={t("searchTitle")} value={query} onChange={setQuery}>
          <Label className="sr-only">{t("searchPlaceholder")}</Label>
          <SearchField.Group>
            <SearchField.SearchIcon />
            <SearchField.Input className="w-full" placeholder={t("searchPlaceholder")} />
            <SearchField.ClearButton />
          </SearchField.Group>
        </SearchField>

        <div className="mt-[12px]">
          <ToggleButtonGroup
            aria-label={t("serviceTypeLabel")}
            className="flex-wrap"
            isDetached
            selectedKeys={[service]}
            selectionMode="single"
            onSelectionChange={(keys) => {
              const next = [...keys][0];
              if (typeof next === "string") setService(next as ServiceKey);
            }}
          >
            {SERVICE_TYPES.map((type) => (
              <ToggleButton className="rounded-full" id={type.key} key={type.key}>
                {type.label}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </div>
      </div>

      {/* Live suggestions directly under the search field. */}
      {hasQuery && (
        <div className="rounded-[var(--radius)] bg-surface-secondary p-[8px] shadow-surface">
          <ResultsList results={results} />
        </div>
      )}
    </div>
  );
}
