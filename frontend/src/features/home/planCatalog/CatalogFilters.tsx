"use client";

import { Accordion, Button, Checkbox, Label, SearchField, Typography } from "@heroui/react";
import { ChevronDown } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import type { ReactNode } from "react";

import { formatPersianNumber } from "@/src/lib/formatters/persian";
import { useSiteConfig } from "@/src/features/site/SiteConfigProvider";

import { RESOURCE_LABELS, type ResourceKey } from "../serviceTypes";

/** Persian ↔ Arabic normalization + English case-insensitive matching. */
function normalizeSearch(value: string): string {
  return value
    .replace(/ي/g, "ی")
    .replace(/ك/g, "ک")
    .replace(/[\u064B-\u0652]/g, "") // strip Persian diacritics
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

type CheckboxOption = { value: string | number; label: string };

function formatResourceValue(
  t: (key: string) => string,
  resource: ResourceKey,
  value: number,
  unit?: string,
) {
  const formatted = formatPersianNumber(value);
  if (resource === "cpu" || unit === "core") {
    return `${formatted} ${t("unitCore")}`;
  }
  if (unit === "GB") {
    if (value >= 1024 && value % 1024 === 0) {
      return `${formatPersianNumber(value / 1024)} ${t("unitTB")}`;
    }
    return `${formatted} ${t("unitGB")}`;
  }
  return unit ? `${formatted} ${unit}` : formatted;
}

function CheckboxList({
  options,
  selected,
  onToggle,
}: {
  options: CheckboxOption[];
  selected: (string | number)[];
  onToggle: (value: string | number) => void;
}) {
  const ot = useTranslations();
  if (!options.length) {
    return <Typography color="muted" type="body-xs">{ot("noFilterOptions")}</Typography>;
  }

  return (
    <div className="flex max-h-[190px] flex-col gap-[9px] overflow-y-auto py-[2px]">
      {options.map((option) => (
        <Checkbox
          isSelected={selected.includes(option.value)}
          key={option.value}
          onChange={() => onToggle(option.value)}
        >
          <Checkbox.Content>
            <Checkbox.Control><Checkbox.Indicator /></Checkbox.Control>
            {option.label}
          </Checkbox.Content>
        </Checkbox>
      ))}
    </div>
  );
}

function FilterDisclosure({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <Accordion.Item id={id}>
      <Accordion.Heading>
        <Accordion.Trigger className="py-[8px] text-[12px] font-semibold">
          {title}
          <Accordion.Indicator><ChevronDown aria-hidden="true" className="size-[15px]" /></Accordion.Indicator>
        </Accordion.Trigger>
      </Accordion.Heading>
      <Accordion.Panel>
        <Accordion.Body className="pb-[12px]">{children}</Accordion.Body>
      </Accordion.Panel>
    </Accordion.Item>
  );
}

function CompanyFilterSection({
  companies,
  selected,
  search,
  onSearchChange,
  onToggle,
}: {
  companies: string[];
  selected: string[];
  search: string;
  onSearchChange: (value: string) => void;
  onToggle: (value: string) => void;
}) {
  const ot = useTranslations();
  const config = useSiteConfig();
  const [expanded, setExpanded] = useState(false);
  const query = normalizeSearch(search);
  const filteredCompanies = companies.filter((name) => normalizeSearch(name).includes(query));
  const visibleCount = config.catalog.companyFilterVisible;
  const visibleCompanies = expanded ? filteredCompanies : filteredCompanies.slice(0, visibleCount);
  const hasNoResults = query.length > 0 && filteredCompanies.length === 0;

  return (
    <FilterDisclosure
      id="companies"
      title={`${ot("companiesFilterTitle")}${selected.length ? ` (${selected.length})` : ""}`}
    >
      <div className="flex flex-col gap-[10px]">
        <SearchField
          aria-label={ot("searchCompany")}
          className="w-full"
          value={search}
          variant="secondary"
          onChange={onSearchChange}
        >
          <Label className="sr-only">{ot("searchCompany")}</Label>
          <SearchField.Group>
            <SearchField.SearchIcon />
            <SearchField.Input className="w-full text-[11px]" placeholder={ot("companyName")} />
            <SearchField.ClearButton />
          </SearchField.Group>
        </SearchField>

        {hasNoResults ? (
          <Typography color="muted" type="body-xs">{ot("companyNotFound")}</Typography>
        ) : (
          <>
            <div className={expanded ? "max-h-[190px] overflow-y-auto" : ""}>
              <CheckboxList
                onToggle={(value) => onToggle(String(value))}
                options={visibleCompanies.map((name) => ({ value: name, label: name }))}
                selected={selected}
              />
            </div>
            {filteredCompanies.length > visibleCount && (
              <Button
                className="justify-between px-0 text-[11px]"
                size="sm"
                variant="ghost"
                onPress={() => setExpanded((value) => !value)}
              >
                {expanded ? ot("showLess") : ot("showAllCount", { count: filteredCompanies.length })}
                <ChevronDown
                  aria-hidden="true"
                  className={`size-[14px] ${expanded ? "rotate-180" : ""}`}
                />
              </Button>
            )}
          </>
        )}
      </div>
    </FilterDisclosure>
  );
}

export function CatalogFilters({
  companies,
  providers,
  onProvidersChange,
  activeResources,
  resourceOptions,
  resourceUnits,
  resourceValues,
  onResourceValuesChange,
  operatingSystems,
  selectedOs,
  onOsChange,
  locations,
  selectedLocations,
  onLocationsChange,
  companySearch,
  onCompanySearchChange,
  onApply,
  isDirty = false,
}: {
  companies: string[];
  providers: string[];
  onProvidersChange: (value: string) => void;
  activeResources: ResourceKey[];
  resourceOptions: (resource: ResourceKey) => number[];
  resourceUnits: Partial<Record<ResourceKey, string>>;
  resourceValues: Partial<Record<ResourceKey, number[]>>;
  onResourceValuesChange: (resource: ResourceKey, value: number) => void;
  operatingSystems: string[];
  selectedOs: string[];
  onOsChange: (value: string) => void;
  locations: string[];
  selectedLocations: string[];
  onLocationsChange: (value: string) => void;
  companySearch: string;
  onCompanySearchChange: (value: string) => void;
  onApply: () => void;
  isDirty?: boolean;
}) {
  const ot = useTranslations();

  return (
    <aside
      className="flex flex-col gap-[16px] rounded-[var(--radius)] border border-[var(--separator)] p-[16px] lg:sticky lg:top-[88px] lg:max-h-[calc(100dvh-112px)] lg:overflow-y-auto lg:rounded-none lg:border-0 lg:border-e lg:pe-[22px]"
    >

      <Typography className="font-semibold" type="body-sm">{ot("filtersLabel")}</Typography>

      <Accordion allowsMultipleExpanded className="w-full">

        <CompanyFilterSection
          companies={companies}
          onSearchChange={onCompanySearchChange}
          onToggle={onProvidersChange}
          search={companySearch}
          selected={providers}
        />
        {activeResources.map((resource) => (
          <FilterDisclosure
            id={`resource-${resource}`}
            key={resource}
            title={`${ot(RESOURCE_LABELS[resource])}${resourceValues[resource]?.length ? ` (${resourceValues[resource]!.length})` : ""}`}
          >
            <CheckboxList
              onToggle={(value) => onResourceValuesChange(resource, Number(value))}
              options={resourceOptions(resource).map((value) => ({
                value,
                label: formatResourceValue(ot, resource, value, resourceUnits[resource]),
              }))}
              selected={resourceValues[resource] ?? []}
            />
          </FilterDisclosure>
        ))}
        {operatingSystems.length > 0 && (
          <FilterDisclosure
            id="operating-system"
            title={`${ot("operatingSystemLabel")}${selectedOs.length ? ` (${selectedOs.length})` : ""}`}
          >
            <CheckboxList
              onToggle={(value) => onOsChange(String(value))}
              options={operatingSystems.map((value) => ({ value, label: value }))}
              selected={selectedOs}
            />
          </FilterDisclosure>
        )}
        {locations.length > 0 && (
          <FilterDisclosure
            id="locations"
            title={`${ot("serverLocationLabel")}${selectedLocations.length ? ` (${selectedLocations.length})` : ""}`}
          >
            <CheckboxList
              onToggle={(value) => onLocationsChange(String(value))}
              options={locations.map((value) => ({ value, label: value }))}
              selected={selectedLocations}
            />
          </FilterDisclosure>
        )}
      </Accordion>
      <Button className="w-full" variant="primary" isDisabled={!isDirty} onPress={onApply}>
        {ot("applyFilters")}
      </Button>
    </aside>
  );
}
