"use client";

import { Accordion, Button, Checkbox, Label, SearchField, Slider, Typography } from "@heroui/react";
import { ChevronDown } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import type { ReactNode } from "react";

import { useSiteConfig } from "@/src/features/site/SiteConfigProvider";

import { RESOURCE_LABELS, type ResourceKey } from "../serviceTypes";
import { formatPrice } from "../planCatalogUtils";

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

function PriceRangeFilter({
  value,
  priceMax,
  onChange,
}: {
  value: number;
  priceMax: number;
  onChange: (value: number) => void;
}) {
  const ot = useTranslations();
  const config = useSiteConfig();
  const step = config.catalog.priceStep;
  const upper = Math.max(step, Math.ceil(Math.max(priceMax, step) / step) * step);
  const clamped = Math.min(upper, Math.max(0, value));

  return (
    <section className="flex flex-col gap-[10px] border-b border-[var(--separator)] pb-[16px]">
      <Label className="font-semibold">{ot("monthlyPriceRange")}</Label>
      {/* No `dir` override: inherits page direction so the thumb follows the drag in both RTL and LTR. */}
      <div>
        <Slider
          aria-label={ot("maxMonthlyPriceAria")}
          maxValue={upper}
          minValue={0}
          step={step}
          value={clamped}
          onChange={(next) => typeof next === "number" && onChange(next)}
        >
          <Slider.Track><Slider.Fill /><Slider.Thumb /></Slider.Track>
        </Slider>
      </div>
      <Typography color="muted" type="body-xs">
        {ot("upToPrice", { price: formatPrice(clamped) })}
      </Typography>
    </section>
  );
}

export function CatalogFilters({
  companies,
  maxPrice,
  priceMax,
  onMaxPriceChange,
  providers,
  onProvidersChange,
  activeResources,
  resourceOptions,
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
  maxPrice: number;
  priceMax: number;
  onMaxPriceChange: (value: number) => void;
  providers: string[];
  onProvidersChange: (value: string) => void;
  activeResources: ResourceKey[];
  resourceOptions: (resource: ResourceKey) => number[];
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
              options={resourceOptions(resource).map((value) => ({ value, label: value.toLocaleString("fa-IR") }))}
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

      <PriceRangeFilter onChange={onMaxPriceChange} priceMax={priceMax} value={maxPrice} />

      <Button className="w-full" variant="primary" isDisabled={!isDirty} onPress={onApply}>
        {ot("applyFilters")}
      </Button>
    </aside>
  );
}
