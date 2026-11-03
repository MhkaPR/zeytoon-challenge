"use client";

import { Button, Skeleton, Tabs, Typography } from "@heroui/react";
import { useTranslations } from "next-intl";
import { RotateCcw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import type { PublicPlan } from "@/src/lib/api/publicCatalog";
import {
  RESOURCE_OPTIONS,
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

const PAGE_SIZES = [8, 12, 20] as const;
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

export function HomePlanCatalog({ plans, loading = false }: { plans: PublicPlan[]; loading?: boolean }) {
  const ot = useTranslations();
  const serviceTabs: { id: ServiceTab; label: string }[] = [
    { id: "all", label: ot("anyOption") },
    ...SERVICE_TYPES.map(({ key, labelKey }) => ({ id: key, label: ot(labelKey) })),
  ];
  const [type, setType] = useState<ServiceTab>("all");
  const [providers, setProviders] = useState<string[]>([]);
  const [maxPrice, setMaxPrice] = useState(1500000);
  const [os, setOs] = useState<string[]>([]);
  const [locations, setLocations] = useState<string[]>([]);
  const [resourceValues, setResourceValues] = useState<Partial<Record<ResourceKey, number[]>>>({});
  const [companySearch, setCompanySearch] = useState("");
  const [sort, setSort] = useState<SortOrder>("default");
  const [pageSize, setPageSize] = useState<number>(PAGE_SIZES[0]);
  const [page, setPage] = useState(1);

  const scopedPlans = useMemo(() => plans.filter((plan) => type === "all" || serviceOf(plan) === type), [plans, type]);
  const activeServices = type === "all" ? SERVICE_TYPES.map(({ key }) => key) : [type];
  const activeResources = useMemo(() => {
    const resourceSets = activeServices.map((service) => new Set(resourcesForType(service)));
    if (!resourceSets.length) return [];
    return [...resourceSets[0]].filter((resource) => resourceSets.every((set) => set.has(resource))) as ResourceKey[];
  }, [type]);
  const companyNames = useMemo(() => [...new Set(scopedPlans.map((plan) => plan.company_name))].sort((a, b) => a.localeCompare(b, "fa")), [scopedPlans]);
  const providerNames = companyNames.filter((name) => name.toLocaleLowerCase("fa").includes(companySearch.trim().toLocaleLowerCase("fa")));
  const operatingSystems = [...new Set(scopedPlans.map((plan) => String(fieldValue(plan, ["operating_system", "os"]) ?? "")).filter(Boolean))].sort((a, b) => a.localeCompare(b, "fa"));
  const availableLocations = [...new Set(scopedPlans.map((plan) => String(fieldValue(plan, ["location", "datacenter_location"]) ?? "")).filter(Boolean))].sort((a, b) => a.localeCompare(b, "fa"));
  const supportsField = (keys: string[]) => activeServices.every((service) => scopedPlans.some((plan) => serviceOf(plan) === service && fieldValue(plan, keys)));
  const activeOperatingSystems = supportsField(["operating_system", "os"]) ? operatingSystems : [];
  const activeLocations = supportsField(["location", "datacenter_location"]) ? availableLocations : [];
  const resourceOptions = (resource: ResourceKey) => {
    const values = [...new Set(scopedPlans.map((plan) => numberValue(fieldValue(plan, RESOURCE_FIELDS[resource]))).filter((value) => value > 0))].sort((a, b) => a - b);
    return values.length ? values : RESOURCE_OPTIONS[resource];
  };

  const filteredPlans = useMemo(() => plans.filter((plan) => {
    const price = priceOf(plan);
    const location = String(fieldValue(plan, ["location", "datacenter_location"]) ?? "");
    const operatingSystem = String(fieldValue(plan, ["operating_system", "os"]) ?? "").toLocaleLowerCase("fa");
    return (type === "all" || serviceOf(plan) === type)
      && (!providers.length || providers.includes(plan.company_name))
      && (!price || price <= maxPrice)
      && (!os.length || os.some((value) => operatingSystem.includes(value)))
      && (!locations.length || locations.includes(location))
      && activeResources.every((resource) => {
        const selected = resourceValues[resource] ?? [];
        const value = numberValue(fieldValue(plan, RESOURCE_FIELDS[resource]));
        return !selected.length || selected.includes(value);
      });
  }), [activeResources, locations, maxPrice, os, plans, providers, resourceValues, type]);

  const sortedPlans = useMemo(() => {
    const result = [...filteredPlans];
    if (sort === "price") return result.sort((a, b) => priceOf(a) - priceOf(b));
    if (sort === "expensive") return result.sort((a, b) => priceOf(b) - priceOf(a));
    return result;
  }, [filteredPlans, sort]);

  const totalPages = Math.max(1, Math.ceil(sortedPlans.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const pagePlans = sortedPlans.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  useEffect(() => {
    setPage(1);
  }, [type, providers, maxPrice, os, locations, resourceValues, sort, pageSize]);

  function toggleString(values: string[], value: string, update: (next: string[]) => void) {
    update(values.includes(value) ? values.filter((item) => item !== value) : [...values, value]);
  }

  function toggleResource(resource: ResourceKey, value: number) {
    setResourceValues((current) => {
      const values = current[resource] ?? [];
      return {
        ...current,
        [resource]: values.includes(value) ? values.filter((item) => item !== value) : [...values, value],
      };
    });
  }

  function resetFilters() {
    setProviders([]);
    setMaxPrice(1500000);
    setOs([]);
    setLocations([]);
    setResourceValues({});
    setCompanySearch("");
    setSort("default");
    setPageSize(PAGE_SIZES[0]);
    setType("all");
    setPage(1);
  }

  return (
    <section className="flex flex-col gap-[24px]" aria-labelledby="home-plans-title">
      <div className="flex flex-col items-start justify-between gap-[12px] sm:flex-row sm:items-end">
        <div className="flex flex-col gap-[6px]">
          <Typography className="text-[22px] font-semibold sm:text-[25px]" id="home-plans-title" type="h2">{ot("homePlansTitle")}</Typography>
          <Typography color="muted" type="body-sm">{ot("homePlansIntro")}</Typography>
        </div>
        <NextLink className="text-[13px] font-semibold text-accent" href="/companies">{ot("viewAllProviders")} ←</NextLink>
      </div>

      <Tabs className="w-full max-w-full" selectedKey={type} onSelectionChange={(key) => setType(String(key) as ServiceTab)} variant="secondary">
        <Tabs.ListContainer className="bg-transparent">
          <Tabs.List aria-label={ot("serviceTabsLabel")} className="w-full max-w-full justify-start gap-[4px] overflow-x-auto">
            {serviceTabs.map((item) => <Tabs.Tab className="w-full px-[10px] py-[6px] text-[12px]" id={item.id} key={item.id}>{item.label}<Tabs.Indicator /></Tabs.Tab>)}
          </Tabs.List>
        </Tabs.ListContainer>
        {serviceTabs.map((item) => <Tabs.Panel className="hidden" id={item.id} key={item.id}> </Tabs.Panel>)}
      </Tabs>

      <div className="grid gap-[24px] lg:grid-cols-[225px_minmax(0,1fr)] lg:gap-[32px]">
        <CatalogFilters
          activeResources={activeResources}
          companies={companyNames}
          companySearch={companySearch}
          locations={activeLocations}
          maxPrice={maxPrice}
          onCompanySearchChange={setCompanySearch}
          onLocationsChange={(value) => toggleString(locations, value, setLocations)}
          onMaxPriceChange={setMaxPrice}
          onOsChange={(value) => toggleString(os, value.toLocaleLowerCase("fa"), setOs)}
          onProvidersChange={(value) => toggleString(providers, value, setProviders)}
          onResourceValuesChange={toggleResource}
          operatingSystems={activeOperatingSystems}
          providers={providers}
          resourceOptions={resourceOptions}
          resourceValues={resourceValues}
          selectedLocations={locations}
          selectedOs={os}
        />

        <div className="min-w-0">
          <div className="mb-[14px] flex flex-col justify-between gap-[12px] sm:flex-row sm:items-center">
            <Typography color="muted" type="body-xs">{ot("plansCount", { count: sortedPlans.length.toLocaleString("fa-IR") })}</Typography>
            <SortAndPageSizeControls onPageSizeChange={setPageSize} onSortChange={setSort} pageSize={pageSize} sort={sort} />
          </div>

          {loading ? (
            <div className="grid gap-[12px] md:grid-cols-2" aria-hidden>
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
            <Button onPress={resetFilters} size="sm" variant="secondary"><RotateCcw aria-hidden="true" className="size-[14px]" />{ot("clearFilters")}</Button>
          </div>
          <div className="mt-[20px]">
            <PlanPagination onPageChange={setPage} page={currentPage} totalPages={totalPages} />
          </div>
        </div>
      </div>
    </section>
  );
}
