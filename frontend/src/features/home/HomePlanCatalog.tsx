"use client";

import { Button, Skeleton, Tabs, Typography } from "@heroui/react";
import { useTranslations } from "next-intl";
import { RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";

import type { PublicPlan } from "@/src/lib/api/publicCatalog";
import { useSiteConfig } from "@/src/features/site/SiteConfigProvider";
import {
  SERVICE_TYPES,
  resourcesForType,
  type ResourceKey,
  type ServiceTypeKey,
} from "./serviceTypes";
import { CatalogFilters } from "./planCatalog/CatalogFilters";
import { PlanCard } from "./planCatalog/PlanCard";
import { PlanPagination, SortAndPageSizeControls } from "./planCatalog/CatalogControls";
import { fieldValue, numberValue, priceOf } from "./planCatalogUtils";
import NextLink from "next/link";

type ServiceTab = "all" | ServiceTypeKey;
type SortOrder = "default" | "price" | "expensive";

export type CatalogFilterValues = {
  providers: string[];
  maxPrice: number;
  os: string[];
  locations: string[];
  resourceValues: Partial<Record<ResourceKey, number[]>>;
};

const SERVICE_FOR_PLAN: Record<string, ServiceTypeKey | undefined> = {
  hosting: "host",
  wordpress: "host",
  virtual_server: "virtual_server",
  vps: "virtual_server",
  dedicated_server: "dedicated_server",
  dedicated: "dedicated_server",
  cdn: "cdn",
};
const RESOURCE_FIELDS: Record<ResourceKey, string[]> = {
  ram: ["ram_amount", "ram"],
  cpu: ["vcpu_cores", "cpu_cores", "cpu"],
  disk: ["storage_amount", "disk_amount", "disk"],
  traffic: ["traffic_amount", "bandwidth_amount", "traffic", "bandwidth"],
};
function serviceOf(plan: PublicPlan): ServiceTypeKey | undefined {
  return SERVICE_FOR_PLAN[plan.plan_type];
}

export function HomePlanCatalog({
  plans,
  loading = false,
  onApplyFilters,
}: {
  plans: PublicPlan[];
  loading?: boolean;
  /** Called with the applied filter values so the parent can refetch from the API. */
  onApplyFilters?: (filters: CatalogFilterValues) => void;
}) {
  const config = useSiteConfig();
  const ot = useTranslations();

  const serviceTabs: { id: ServiceTab; label: string }[] = [
    { id: "all", label: ot("anyOption") },
    ...SERVICE_TYPES.map(({ key, labelKey }) => ({ id: key, label: ot(labelKey) })),
  ];

  const [type, setType] = useState<ServiceTab>("all");
  const [companySearch, setCompanySearch] = useState("");
  const [sort, setSort] = useState<SortOrder>("default");
  const [pageSize, setPageSize] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const effectivePageSize = pageSize ?? config.catalog.defaultPageSize;

  // Max slider value derived from real data → position at max == "no price filter".
  const priceMax = useMemo(() => {
    const prices = plans
      .map((plan) => priceOf(plan))
      .filter((value): value is number => typeof value === "number" && value > 0);
    const max = prices.length ? Math.max(...prices) : config.catalog.priceMax;
    return Math.max(
      config.catalog.priceMin,
      Math.ceil(max / config.catalog.priceStep) * config.catalog.priceStep +
        config.catalog.priceStep,
    );
  }, [config.catalog.priceMax, config.catalog.priceMin, config.catalog.priceStep, plans]);

  const makeDefaults = (): CatalogFilterValues => ({
    providers: [],
    maxPrice: priceMax,
    os: [],
    locations: [],
    resourceValues: {},
  });

  const [draft, setDraft] = useState<CatalogFilterValues>(makeDefaults);
  const [applied, setApplied] = useState<CatalogFilterValues>(makeDefaults);
  const [isDirty, setIsDirty] = useState(false);

  const scopedPlans = useMemo(
    () => plans.filter((plan) => type === "all" || serviceOf(plan) === type),
    [plans, type],
  );

  const activeServices = type === "all" ? SERVICE_TYPES.map(({ key }) => key) : [type];

  const activeResources = useMemo(() => {
    const resourceSets = activeServices.map((service) => new Set(resourcesForType(service)));
    if (!resourceSets.length) return [];
    return [...resourceSets[0]].filter((resource) =>
      resourceSets.every((set) => set.has(resource)),
    ) as ResourceKey[];
  }, [type]); // eslint-disable-line react-hooks/exhaustive-deps

  const companyNames = useMemo(
    () =>
      [...new Set(scopedPlans.map((plan) => plan.company_name))].sort((a, b) =>
        a.localeCompare(b, "fa"),
      ),
    [scopedPlans],
  );

  const operatingSystems = useMemo(
    () =>
      [...new Set(
        scopedPlans
          .map((plan) => String(fieldValue(plan, ["operating_system", "os"]) ?? ""))
          .filter(Boolean),
      )].sort((a, b) => a.localeCompare(b, "fa")),
    [scopedPlans],
  );

  const availableLocations = useMemo(
    () =>
      [...new Set(
        scopedPlans
          .map((plan) => String(fieldValue(plan, ["location", "datacenter_location"]) ?? ""))
          .filter(Boolean),
      )].sort((a, b) => a.localeCompare(b, "fa")),
    [scopedPlans],
  );

  const supportsField = (keys: string[]) =>
    activeServices.every((service) =>
      scopedPlans.some((plan) => serviceOf(plan) === service && fieldValue(plan, keys)),
    );

  const activeOperatingSystems = supportsField(["operating_system", "os"]) ? operatingSystems : [];
  const activeLocations = supportsField(["location", "datacenter_location"]) ? availableLocations : [];

  const resourceOptions = (resource: ResourceKey) => {
    const values = [...new Set(
      scopedPlans
        .map((plan) => numberValue(fieldValue(plan, RESOURCE_FIELDS[resource])))
        .filter((value) => value > 0),
    )].sort((a, b) => a - b);
    return values.length ? values : config.catalog.resourceOptions[resource];
  };

  // Filtering uses APPLIED — nothing changes until the user clicks Apply.
  const filteredPlans = useMemo(() => plans.filter((plan) => {
    const price = priceOf(plan);
    const location = String(fieldValue(plan, ["location", "datacenter_location"]) ?? "");
    const operatingSystem = String(fieldValue(plan, ["operating_system", "os"]) ?? "").toLowerCase();

    return (type === "all" || serviceOf(plan) === type)
      && (!applied.providers.length || applied.providers.includes(plan.company_name))
      && (!price || price <= applied.maxPrice)
      && (!applied.os.length || applied.os.some((value) => operatingSystem.includes(value.toLowerCase())))
      && (!applied.locations.length || applied.locations.includes(location))
      && activeResources.every((resource) => {
        const selected = applied.resourceValues[resource] ?? [];
        const value = numberValue(fieldValue(plan, RESOURCE_FIELDS[resource]));
        return !selected.length || selected.includes(value);
      });
  }), [activeResources, applied, plans, type]);

  const sortedPlans = useMemo(() => {
    const result = [...filteredPlans];
    if (sort === "price") return result.sort((a, b) => priceOf(a) - priceOf(b));
    if (sort === "expensive") return result.sort((a, b) => priceOf(b) - priceOf(a));
    return result;
  }, [filteredPlans, sort]);

  const totalPages = Math.max(1, Math.ceil(sortedPlans.length / effectivePageSize));
  const currentPage = Math.min(page, totalPages);
  const pagePlans = sortedPlans.slice(
    (currentPage - 1) * effectivePageSize,
    currentPage * effectivePageSize,
  );

  // useEffect(() => {
  //   setPage(1);
  // }, [type, applied, sort, pageSize]);

  function updateDraft(patch: Partial<CatalogFilterValues>) {
    setDraft((prev) => ({ ...prev, ...patch }));
    setIsDirty(true);
  }

  function toggleDraftArray<K extends "providers" | "os" | "locations">(key: K, value: string) {
    setDraft((prev) => {
      const arr = prev[key];
      return { ...prev, [key]: arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value] };
    });
    setIsDirty(true);
  }

  function toggleDraftResource(resource: ResourceKey, value: number) {
    setDraft((prev) => {
      const values = prev.resourceValues[resource] ?? [];
      return {
        ...prev,
        resourceValues: {
          ...prev.resourceValues,
          [resource]: values.includes(value) ? values.filter((v) => v !== value) : [...values, value],
        },
      };
    });
    setIsDirty(true);
  }

  function applyFilters() {
    setApplied(draft);
    setIsDirty(false);
    setPage(1);
    onApplyFilters?.(draft);
  }

  function resetFilters() {
    const next = makeDefaults();
    setDraft(next);
    setApplied(next);
    setIsDirty(false);
    setCompanySearch("");
    setSort("default");
    setPageSize(null);
    setType("all");
    setPage(1);
  }

  return (
    <section aria-labelledby="home-plans-title" className="flex flex-col gap-[24px]">
      <div className="flex flex-col items-start justify-between gap-[12px] sm:flex-row sm:items-end">
        <div className="flex flex-col gap-[6px]">
          <Typography className="text-[22px] font-semibold sm:text-[25px]" id="home-plans-title" type="h2">
            {ot("homePlansTitle")}
          </Typography>
          <Typography color="muted" type="body-sm">{ot("homePlansIntro")}</Typography>
        </div>
        <NextLink className="text-[13px] font-semibold text-accent" href="/companies">
          {ot("viewAllProviders")} ←
        </NextLink>
      </div>

      <Tabs
        className="w-full max-w-full"
        selectedKey={type}
        variant="secondary"
        onSelectionChange={(key) => setType(String(key) as ServiceTab)}
      >
        <Tabs.ListContainer className="bg-transparent">
          <Tabs.List aria-label={ot("serviceTabsLabel")} className="w-full max-w-full justify-start gap-[4px] overflow-x-auto">
            {serviceTabs.map((item) => (
              <Tabs.Tab className="w-full px-[10px] py-[6px] text-[12px]" id={item.id} key={item.id}>
                {item.label}
                <Tabs.Indicator />
              </Tabs.Tab>
            ))}
          </Tabs.List>
        </Tabs.ListContainer>
        {serviceTabs.map((item) => (
          <Tabs.Panel className="hidden" id={item.id} key={item.id}> </Tabs.Panel>
        ))}
      </Tabs>

      <div className="grid gap-[24px] lg:grid-cols-[225px_minmax(0,1fr)] lg:items-start lg:gap-[32px]">
        <CatalogFilters
          activeResources={activeResources}
          companies={companyNames}
          companySearch={companySearch}
          isDirty={isDirty}
          locations={activeLocations}
          maxPrice={draft.maxPrice}
          operatingSystems={activeOperatingSystems}
          priceMax={priceMax}
          providers={draft.providers}
          resourceOptions={resourceOptions}
          resourceValues={draft.resourceValues}
          selectedLocations={draft.locations}
          selectedOs={draft.os}
          onApply={applyFilters}
          onCompanySearchChange={setCompanySearch}
          onLocationsChange={(value) => toggleDraftArray("locations", value)}
          onMaxPriceChange={(value) => updateDraft({ maxPrice: value })}
          onOsChange={(value) => toggleDraftArray("os", value)}
          onProvidersChange={(value) => toggleDraftArray("providers", value)}
          onResourceValuesChange={toggleDraftResource}
        />

        <div className="min-w-0">
          <div className="mb-[14px] flex flex-col justify-between gap-[12px] sm:flex-row sm:items-center">
            <Typography color="muted" type="body-xs">
              {ot("plansCount", { count: sortedPlans.length.toLocaleString("fa-IR") })}
            </Typography>
            <SortAndPageSizeControls
              onPageSizeChange={setPageSize}
              onSortChange={setSort}
              pageSize={effectivePageSize}
              sort={sort}
            />
          </div>

          {loading ? (
            <div aria-hidden className="grid gap-[12px] md:grid-cols-2">
              {Array.from({ length: 4 }, (_, index) => (
                <Skeleton className="h-[180px] rounded-[var(--radius)]" key={index} />
              ))}
            </div>
          ) : pagePlans.length ? (
            <div className="grid gap-[12px] md:grid-cols-2">
              {pagePlans.map((plan) => <PlanCard key={plan.id} plan={plan} />)}
            </div>
          ) : (
            <div className="py-[36px] text-center text-[13px] text-muted">
              {plans.length ? ot("noPlansForFilters") : ot("noPlansPublished")}
            </div>
          )}

          <div className="mt-[18px] flex flex-col items-center justify-between gap-[14px] sm:flex-row">
            <Typography color="muted" type="body-xs">{ot("plansDataNote")}</Typography>
            <Button onPress={resetFilters} size="sm" variant="secondary">
              <RotateCcw aria-hidden="true" className="size-[14px]" />
              {ot("clearFilters")}
            </Button>
          </div>

          <div className="mt-[20px]">
            <PlanPagination onPageChange={setPage} page={currentPage} totalPages={totalPages} />
          </div>
        </div>
      </div>
    </section>
  );
}
