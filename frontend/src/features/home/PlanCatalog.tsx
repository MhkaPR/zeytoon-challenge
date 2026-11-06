"use client";

import {
  Button,
  Pagination,
  Skeleton,
  Tabs,
  Typography,
} from "@heroui/react";
import { RotateCcw } from "lucide-react";
import NextLink from "next/link";
import { useTranslations } from "next-intl";
import { Fragment, useMemo, useRef, useState, type ReactNode } from "react";

import { useSiteConfig } from "@/src/features/site/SiteConfigProvider";
import {
  getPlansPage,
  type PlansPage,
  type PublicPlan,
} from "@/src/lib/api/publicCatalog";

import {
  SERVICE_TYPES,
  resourcesForType,
  type ResourceKey,
  type ServiceTypeKey,
} from "./serviceTypes";
import { CatalogFilters } from "./planCatalog/CatalogFilters";
import { PlanCard } from "./planCatalog/PlanCard";
import { SortAndPageSizeControls } from "./planCatalog/CatalogControls";

type ServiceTab = "all" | ServiceTypeKey;
type SortOrder = "default" | "price" | "expensive";

export type CatalogFilterValues = {
  providers: string[];
  os: string[];
  locations: string[];
  resourceValues: Partial<Record<ResourceKey, number[]>>;
};

export type PlanCatalogFilterContext = {
  type: ServiceTab;
  draft: CatalogFilterValues;
  sort: SortOrder;
  companySearch: string;
  isDirty: boolean;
  activeResources: ResourceKey[];
  facets: PlansPage["facets"];
  pageSize: number;
  defaultFilters: ReactNode;
  actions: {
    onTypeChange: (type: ServiceTab) => void;
    onToggleProvider: (value: string) => void;
    onToggleOs: (value: string) => void;
    onToggleLocation: (value: string) => void;
    onToggleResource: (resource: ResourceKey, value: number) => void;
    onCompanySearchChange: (value: string) => void;
    onApply: () => void;
    onReset: () => void;
  };
};

export type PlanCatalogToolbarContext = {
  data: PlansPage;
  page: number;
  pageSize: number;
  sort: SortOrder;
  onSortChange: (value: SortOrder) => void;
  onPageSizeChange: (value: number) => void;
};

export type PlanCatalogProps = {
  plansPage: PlansPage;
  searchParams?: Record<string, string | string[] | undefined>;
  baseParams?: Record<string, string | string[] | undefined>;
  loading?: boolean;
  title?: ReactNode;
  description?: ReactNode;
  headerAction?: ReactNode;
  filters?: ReactNode | ((context: PlanCatalogFilterContext) => ReactNode);
  toolbar?: ReactNode | ((context: PlanCatalogToolbarContext) => ReactNode);
  renderPlan?: (plan: PublicPlan) => ReactNode;
  emptyState?: ReactNode | ((context: { hasActiveFilters: boolean }) => ReactNode);
  footer?: ReactNode | ((context: { hasActiveFilters: boolean; onReset: () => void }) => ReactNode);
  showServiceTabs?: boolean;
  showSort?: boolean;
  showPagination?: boolean;
  ariaLabel?: string;
  className?: string;
};

const RESOURCE_KEYS: ResourceKey[] = ["ram", "cpu", "disk", "traffic"];

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

function buildParams({
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
}): Record<string, string> {
  const params: Record<string, string> = {};
  if (type !== "all") params.type = type;
  if (draft.providers.length) params.providers = draft.providers.join(",");
  if (draft.os.length) params.os = draft.os.join(",");
  if (draft.locations.length) params.location = draft.locations.join(",");
  for (const key of RESOURCE_KEYS) {
    const values = draft.resourceValues[key];
    if (values?.length) params[key] = values.join(",");
  }
  if (sort !== "default") params.sort = sort;
  params.page = String(page);
  params.page_size = String(pageSize);
  return params;
}

function CatalogPagination({
  page,
  totalPages,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}) {
  const ot = useTranslations();
  if (totalPages <= 1) return null;

  const pages: (number | "ellipsis")[] = [];
  if (totalPages <= 7) {
    pages.push(...Array.from({ length: totalPages }, (_, index) => index + 1));
  } else {
    pages.push(1);
    if (page > 3) pages.push("ellipsis");
    for (
      let current = Math.max(2, page - 1);
      current <= Math.min(totalPages - 1, page + 1);
      current += 1
    ) {
      pages.push(current);
    }
    if (page < totalPages - 2) pages.push("ellipsis");
    pages.push(totalPages);
  }

  return (
    <Pagination aria-label={ot("paginationLabel")} className="justify-center" size="sm">
      <Pagination.Content>
        <Pagination.Item>
          <Pagination.Previous isDisabled={page === 1} onPress={() => onPageChange(page - 1)}>
            <Pagination.PreviousIcon />
            <span>{ot("previousPage")}</span>
          </Pagination.Previous>
        </Pagination.Item>
        {pages.map((item, index) =>
          item === "ellipsis" ? (
            <Pagination.Item key={`ellipsis-${index}`}>
              <Pagination.Ellipsis />
            </Pagination.Item>
          ) : (
            <Pagination.Item key={item}>
              <Pagination.Link isActive={item === page} onPress={() => onPageChange(item)}>
                {item.toLocaleString("fa-IR")}
              </Pagination.Link>
            </Pagination.Item>
          ),
        )}
        <Pagination.Item>
          <Pagination.Next isDisabled={page === totalPages} onPress={() => onPageChange(page + 1)}>
            <span>{ot("nextPage")}</span>
            <Pagination.NextIcon />
          </Pagination.Next>
        </Pagination.Item>
      </Pagination.Content>
    </Pagination>
  );
}

function CatalogSkeleton() {
  return (
    <div aria-hidden className="grid gap-[12px] md:grid-cols-2" data-testid="plan-catalog-skeleton">
      {Array.from({ length: 4 }, (_, index) => (
        <div
          className="flex h-[180px] flex-col gap-[16px] rounded-[var(--radius)] border border-[var(--separator)] p-[18px]"
          key={index}
        >
          <div className="flex items-start justify-between gap-[16px]">
            <div className="flex flex-col gap-[8px]">
              <Skeleton className="h-[18px] w-[150px] rounded-[6px]" />
              <Skeleton className="h-[32px] w-[120px] rounded-[8px]" />
            </div>
            <Skeleton className="h-[18px] w-[72px] rounded-[6px]" />
          </div>
          <div className="grid grid-cols-2 gap-[10px] border-t border-[var(--separator)] pt-[14px]">
            {Array.from({ length: 4 }, (_, item) => (
              <Skeleton className="h-[24px] rounded-[6px]" key={item} />
            ))}
          </div>
          <div className="mt-auto flex gap-[8px]">
            <Skeleton className="h-[34px] flex-1 rounded-[8px]" />
            <Skeleton className="h-[34px] flex-1 rounded-[8px]" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function PlanCatalog({
  plansPage,
  searchParams = {},
  baseParams = {},
  loading = false,
  title,
  description,
  headerAction,
  filters,
  toolbar,
  renderPlan,
  emptyState,
  footer,
  showServiceTabs = true,
  showSort = true,
  showPagination = true,
  ariaLabel,
  className,
}: PlanCatalogProps) {
  const config = useSiteConfig();
  const ot = useTranslations();
  const [data, setData] = useState(plansPage);
  const [page, setPage] = useState(plansPage.page);
  const [pageSize, setPageSize] = useState(
    plansPage.pageSize || config.catalog.defaultPageSize,
  );
  const [type, setType] = useState<ServiceTab>(() => parseType(searchParams.type));
  const [draft, setDraft] = useState<CatalogFilterValues>(() => parseDraft(searchParams));
  const [sort, setSort] = useState<SortOrder>(() => parseSort(searchParams.sort));
  const [companySearch, setCompanySearch] = useState("");
  const [isDirty, setIsDirty] = useState(false);
  const [isFetching, setIsFetching] = useState(false);
  const requestIdRef = useRef(0);

  const serviceTabs: { id: ServiceTab; label: string }[] = [
    { id: "all", label: ot("anyOption") },
    ...SERVICE_TYPES.map(({ key, labelKey }) => ({ id: key, label: ot(labelKey) })),
  ];

  const activeResources = useMemo(
    () => (type === "all" ? RESOURCE_KEYS : resourcesForType(type)),
    [type],
  );

  async function loadPage(
    nextPage: number,
    overrides: {
      type?: ServiceTab;
      draft?: CatalogFilterValues;
      sort?: SortOrder;
      pageSize?: number;
    } = {},
  ) {
    const nextType = overrides.type ?? type;
    const nextDraft = overrides.draft ?? draft;
    const nextSort = overrides.sort ?? sort;
    const nextPageSize = overrides.pageSize ?? pageSize;
    const request = requestIdRef.current + 1;
    requestIdRef.current = request;
    setIsFetching(true);
    try {
      const next = await getPlansPage({
        ...baseParams,
        ...buildParams({
          type: nextType,
          draft: nextDraft,
          sort: nextSort,
          page: nextPage,
          pageSize: nextPageSize,
        }),
      });
      if (request !== requestIdRef.current) return;
      setData(next);
      setPage(next.page || nextPage);
    } finally {
      if (request === requestIdRef.current) setIsFetching(false);
    }
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

  function changeType(next: ServiceTab) {
    const nextResources = new Set(
      next === "all" ? RESOURCE_KEYS : resourcesForType(next),
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
    void loadPage(1, { type: next, draft: nextDraft });
  }

  function applyFilters() {
    setIsDirty(false);
    void loadPage(1, { draft });
  }

  function resetFilters() {
    const defaults = makeDefaults();
    setDraft(defaults);
    setType("all");
    setSort("default");
    setCompanySearch("");
    setIsDirty(false);
    void loadPage(1, { type: "all", draft: defaults, sort: "default" });
  }

  function changeSort(value: SortOrder) {
    setSort(value);
    void loadPage(1, { sort: value });
  }

  function changePageSize(value: number) {
    setPageSize(value);
    void loadPage(1, { pageSize: value });
  }

  const hasActiveFilters =
    type !== "all" ||
    draft.providers.length > 0 ||
    draft.os.length > 0 ||
    draft.locations.length > 0 ||
    RESOURCE_KEYS.some((key) => (draft.resourceValues[key]?.length ?? 0) > 0);

  const filtersEnabled = filters !== false && filters !== null;
  const defaultFilters = (
    <CatalogFilters
      activeResources={activeResources}
      companies={data.facets.companies}
      companySearch={companySearch}
      isDirty={isDirty}
      locations={data.facets.locations}
      operatingSystems={data.facets.operating_systems}
      providers={draft.providers}
      resourceOptions={(resource) =>
        data.facets.resources[resource]?.length
          ? data.facets.resources[resource]
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
  );

  const filterContext: PlanCatalogFilterContext = {
    type,
    draft,
    sort,
    companySearch,
    isDirty,
    activeResources,
    facets: data.facets,
    pageSize,
    defaultFilters,
    actions: {
      onTypeChange: changeType,
      onToggleProvider: (value) => toggleDraftArray("providers", value),
      onToggleOs: (value) => toggleDraftArray("os", value),
      onToggleLocation: (value) => toggleDraftArray("locations", value),
      onToggleResource: toggleDraftResource,
      onCompanySearchChange: setCompanySearch,
      onApply: applyFilters,
      onReset: resetFilters,
    },
  };

  const renderedFilters =
    filters === undefined
      ? defaultFilters
      : typeof filters === "function"
        ? filters(filterContext)
        : filters;

  const toolbarContext: PlanCatalogToolbarContext = {
    data,
    page,
    pageSize,
    sort,
    onSortChange: changeSort,
    onPageSizeChange: changePageSize,
  };

  const defaultToolbar = (
    <div className="mb-[14px] flex flex-col justify-between gap-[12px] sm:flex-row sm:items-center">
      <Typography color="muted" type="body-xs">
        {ot("plansCount", { count: data.count.toLocaleString("fa-IR") })}
      </Typography>
      {showSort && (
        <SortAndPageSizeControls
          onPageSizeChange={changePageSize}
          onSortChange={changeSort}
          pageSize={pageSize}
          sort={sort}
        />
      )}
    </div>
  );

  const renderedToolbar =
    toolbar === undefined
      ? defaultToolbar
      : typeof toolbar === "function"
        ? toolbar(toolbarContext)
        : toolbar;

  const defaultEmptyState = (
    <div className="py-[36px] text-center text-[13px] text-muted">
      {hasActiveFilters ? ot("noPlansForFilters") : ot("noPlansPublished")}
    </div>
  );

  const renderedEmptyState =
    emptyState === undefined
      ? defaultEmptyState
      : typeof emptyState === "function"
        ? emptyState({ hasActiveFilters })
        : emptyState;

  const defaultFooter = (
    <div className="mt-[18px] flex flex-col items-center justify-between gap-[14px] sm:flex-row">
      <Typography color="muted" type="body-xs">{ot("plansDataNote")}</Typography>
      {filtersEnabled && (
        <Button onPress={resetFilters} size="sm" variant="secondary">
          <RotateCcw aria-hidden="true" className="size-[14px]" />
          {ot("clearFilters")}
        </Button>
      )}
    </div>
  );

  const renderedFooter =
    footer === undefined
      ? defaultFooter
      : typeof footer === "function"
        ? footer({ hasActiveFilters, onReset: resetFilters })
        : footer;

  const renderedTitle = title === undefined ? ot("homePlansTitle") : title;
  const renderedDescription = description === undefined ? ot("homePlansIntro") : description;
  const renderedHeaderAction =
    headerAction === undefined ? (
      <NextLink className="text-[13px] font-semibold text-accent" href="/companies">
        {ot("viewAllProviders")} ←
      </NextLink>
    ) : (
      headerAction
    );
  const hasHeader =
    renderedTitle !== null ||
    renderedDescription !== null ||
    renderedHeaderAction !== null;

  return (
    <section
      aria-label={ariaLabel ?? ot("homePlansTitle")}
      className={`flex flex-col gap-[24px] ${className ?? ""}`}
    >
      {hasHeader && (
        <div className="flex flex-col items-start justify-between gap-[12px] sm:flex-row sm:items-end">
          <div className="flex flex-col gap-[6px]">
            {renderedTitle !== null && (
              <Typography className="text-[22px] font-semibold sm:text-[25px]" type="h2">
                {renderedTitle}
              </Typography>
            )}
            {renderedDescription !== null && (
              <Typography color="muted" type="body-sm">{renderedDescription}</Typography>
            )}
          </div>
          {renderedHeaderAction}
        </div>
      )}

      {showServiceTabs && (
        <Tabs
          className="w-full max-w-full"
          selectedKey={type}
          variant="secondary"
          onSelectionChange={(key) => changeType(String(key) as ServiceTab)}
        >
          <Tabs.ListContainer className="bg-transparent">
            <Tabs.List
              aria-label={ot("serviceTabsLabel")}
              className="w-full max-w-full justify-start gap-[4px] overflow-x-auto"
            >
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
      )}

      <div
        className={
          filtersEnabled
            ? "grid gap-[24px] lg:grid-cols-[225px_minmax(0,1fr)] lg:items-start lg:gap-[32px]"
            : "min-w-0"
        }
      >
        {filtersEnabled && renderedFilters}

        <div className="min-w-0" aria-busy={loading || isFetching}>
          {renderedToolbar}

          {loading || isFetching ? (
            <CatalogSkeleton />
          ) : data.plans.length ? (
            <div className="grid gap-[12px] md:grid-cols-2">
              {data.plans.map((plan) => (
                <Fragment key={plan.id}>
                  {renderPlan ? renderPlan(plan) : <PlanCard plan={plan} />}
                </Fragment>
              ))}
            </div>
          ) : (
            renderedEmptyState
          )}

          {renderedFooter}

          {showPagination && (
            <div className="mt-[20px]">
              <CatalogPagination
                onPageChange={(nextPage) => void loadPage(nextPage)}
                page={page}
                totalPages={data.totalPages}
              />
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
