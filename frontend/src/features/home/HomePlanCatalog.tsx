"use client";

import { Button, Skeleton, Tabs, Typography } from "@heroui/react";
import { useTranslations } from "next-intl";
import { RotateCcw } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useMemo, useState, useTransition } from "react";

import type { PlansPage } from "@/src/lib/api/publicCatalog";
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
import NextLink from "next/link";

type ServiceTab = "all" | ServiceTypeKey;
type SortOrder = "default" | "price" | "expensive";

export type CatalogFilterValues = {
  providers: string[];
  os: string[];
  locations: string[];
  resourceValues: Partial<Record<ResourceKey, number[]>>;
};

const RESOURCE_KEYS: ResourceKey[] = ["ram", "cpu", "disk", "traffic"];

function resourcesForServices(services: ServiceTypeKey[]): ResourceKey[] {
  const sets = services.map((service) => new Set(resourcesForType(service)));
  if (!sets.length) return [];
  return [...sets[0]].filter((resource) =>
    sets.every((set) => set.has(resource)),
  ) as ResourceKey[];
}

function first(value: string | string[] | undefined): string {
  return Array.isArray(value) ? (value[0] ?? "") : (value ?? "");
}

function parseList(value: string | string[] | undefined): string[] {
  return first(value)
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseType(value: string | string[] | undefined): ServiceTab {
  const parsed = first(value);
  return SERVICE_TYPES.some(({ key }) => key === parsed) ? (parsed as ServiceTypeKey) : "all";
}

function parseSort(value: string | string[] | undefined): SortOrder {
  const parsed = first(value);
  return parsed === "price" || parsed === "expensive" ? parsed : "default";
}

function makeDefaults(): CatalogFilterValues {
  return { providers: [], os: [], locations: [], resourceValues: {} };
}

function parseDraft(params: Record<string, string | string[] | undefined>): CatalogFilterValues {
  const resourceValues: Partial<Record<ResourceKey, number[]>> = {};
  for (const key of RESOURCE_KEYS) {
    const values = parseList(params[key])
      .map((value) => Number(value))
      .filter((value) => Number.isFinite(value));
    if (values.length) resourceValues[key] = values;
  }
  return {
    providers: parseList(params.providers),
    os: parseList(params.os),
    locations: parseList(params.location),
    resourceValues,
  };
}

function buildQuery({
  type,
  draft,
  sort,
  page,
  pageSize,
}: {
  type: ServiceTab;
  draft: CatalogFilterValues;
  sort: SortOrder;
  page: number;
  pageSize: number;
}): string {
  const params = new URLSearchParams();
  if (type !== "all") params.set("type", type);
  if (draft.providers.length) params.set("providers", draft.providers.join(","));
  if (draft.os.length) params.set("os", draft.os.join(","));
  if (draft.locations.length) params.set("location", draft.locations.join(","));
  for (const key of RESOURCE_KEYS) {
    const values = draft.resourceValues[key];
    if (values?.length) params.set(key, values.join(","));
  }
  if (sort !== "default") params.set("sort", sort);
  if (page > 1) params.set("page", String(page));
  params.set("page_size", String(pageSize));
  return params.toString();
}

export function HomePlanCatalog({
  plansPage,
  searchParams,
  loading = false,
}: {
  plansPage: PlansPage;
  searchParams: Record<string, string | string[] | undefined>;
  loading?: boolean;
}) {
  const config = useSiteConfig();
  const ot = useTranslations();
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();

  const [type, setType] = useState<ServiceTab>(() => parseType(searchParams.type));
  const [draft, setDraft] = useState<CatalogFilterValues>(() => parseDraft(searchParams));
  const [sort, setSort] = useState<SortOrder>(() => parseSort(searchParams.sort));
  const [companySearch, setCompanySearch] = useState("");
  const [isDirty, setIsDirty] = useState(false);
  const pageSize = plansPage.pageSize || config.catalog.defaultPageSize;

  const serviceTabs: { id: ServiceTab; label: string }[] = [
    { id: "all", label: ot("anyOption") },
    ...SERVICE_TYPES.map(({ key, labelKey }) => ({ id: key, label: ot(labelKey) })),
  ];

  const activeResources = useMemo(
    () =>
      resourcesForServices(
        type === "all" ? SERVICE_TYPES.map(({ key }) => key) : [type],
      ),
    [type],
  );

  function navigate(overrides: {
    type?: ServiceTab;
    draft?: CatalogFilterValues;
    sort?: SortOrder;
    page?: number;
  }) {
    const query = buildQuery({
      type: overrides.type ?? type,
      draft: overrides.draft ?? draft,
      sort: overrides.sort ?? sort,
      page: overrides.page ?? 1,
      pageSize,
    });
    startTransition(() => router.push(query ? `${pathname}?${query}` : pathname));
  }

  function toggleDraftArray<K extends "providers" | "os" | "locations">(key: K, value: string) {
    setDraft((prev) => {
      const values = prev[key];
      return {
        ...prev,
        [key]: values.includes(value)
          ? values.filter((item) => item !== value)
          : [...values, value],
      };
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
          [resource]: values.includes(value)
            ? values.filter((item) => item !== value)
            : [...values, value],
        },
      };
    });
    setIsDirty(true);
  }

  function applyFilters() {
    setIsDirty(false);
    navigate({ draft, page: 1 });
  }

  function resetFilters() {
    setDraft(makeDefaults());
    setType("all");
    setSort("default");
    setCompanySearch("");
    setIsDirty(false);
    startTransition(() => router.push(pathname));
  }

  const hasActiveFilters =
    type !== "all" ||
    draft.providers.length > 0 ||
    draft.os.length > 0 ||
    draft.locations.length > 0 ||
    RESOURCE_KEYS.some((key) => (draft.resourceValues[key]?.length ?? 0) > 0);

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
        onSelectionChange={(key) => {
          const next = String(key) as ServiceTab;
          const nextResources = new Set(
            resourcesForServices(
              next === "all" ? SERVICE_TYPES.map(({ key: service }) => service) : [next],
            ),
          );
          const nextDraft: CatalogFilterValues = {
            ...draft,
            resourceValues: Object.fromEntries(
              Object.entries(draft.resourceValues).filter(([resource]) =>
                nextResources.has(resource as ResourceKey),
              ),
            ),
          };
          setType(next);
          setDraft(nextDraft);
          setIsDirty(false);
          navigate({ type: next, draft: nextDraft, page: 1 });
        }}
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
          companies={plansPage.facets.companies}
          companySearch={companySearch}
          isDirty={isDirty}
          locations={plansPage.facets.locations}
          operatingSystems={plansPage.facets.operating_systems}
          providers={draft.providers}
          resourceOptions={(resource) =>
            plansPage.facets.resources[resource]?.length
              ? plansPage.facets.resources[resource]
              : config.catalog.resourceOptions[resource]
          }
          resourceValues={draft.resourceValues}
          selectedLocations={draft.locations}
          selectedOs={draft.os}
          onApply={applyFilters}
          onCompanySearchChange={setCompanySearch}
          onLocationsChange={(value) => toggleDraftArray("locations", value)}
          onOsChange={(value) => toggleDraftArray("os", value)}
          onProvidersChange={(value) => toggleDraftArray("providers", value)}
          onResourceValuesChange={toggleDraftResource}
        />

        <div className="min-w-0">
          <div className="mb-[14px] flex flex-col justify-between gap-[12px] sm:flex-row sm:items-center">
            <Typography color="muted" type="body-xs">
              {ot("plansCount", { count: plansPage.count.toLocaleString("fa-IR") })}
            </Typography>
            <SortAndPageSizeControls
              onPageSizeChange={() => undefined}
              onSortChange={(value) => {
                setSort(value);
                navigate({ sort: value, page: 1 });
              }}
              pageSize={pageSize}
              sort={sort}
            />
          </div>

          {loading || isPending ? (
            <div aria-hidden className="grid gap-[12px] md:grid-cols-2">
              {Array.from({ length: 4 }, (_, index) => (
                <Skeleton className="h-[180px] rounded-[var(--radius)]" key={index} />
              ))}
            </div>
          ) : plansPage.plans.length ? (
            <div className="grid gap-[12px] md:grid-cols-2">
              {plansPage.plans.map((plan) => <PlanCard key={plan.id} plan={plan} />)}
            </div>
          ) : (
            <div className="py-[36px] text-center text-[13px] text-muted">
              {hasActiveFilters ? ot("noPlansForFilters") : ot("noPlansPublished")}
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
            <PlanPagination
              onPageChange={(page) => navigate({ page })}
              page={plansPage.page}
              totalPages={plansPage.totalPages}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
