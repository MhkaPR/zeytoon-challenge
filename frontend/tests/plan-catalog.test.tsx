import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PlanCatalog } from "@/src/features/home/PlanCatalog";
import type { PlansPage, PublicPlan } from "@/src/lib/api/publicCatalog";
import { strings } from "./messages";

const { getPlansPage } = vi.hoisted(() => ({
  getPlansPage: vi.fn(),
}));

vi.mock("@/src/lib/api/publicCatalog", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/src/lib/api/publicCatalog")>();
  return { ...actual, getPlansPage };
});

function plan(id: number, name: string): PublicPlan {
  return {
    id,
    domain: `host-${id}.example`,
    company_name: `Host ${id}`,
    plan_type: "host",
    values: { plan_name: name, price: 100000 },
    published_at: null,
  };
}

function page(overrides: Partial<PlansPage> = {}): PlansPage {
  return {
    plans: [plan(1, "Plan one")],
    count: 2,
    page: 1,
    pageSize: 1,
    totalPages: 2,
    facets: {
      companies: [],
      operating_systems: [],
      locations: [],
      resources: { ram: [], cpu: [], disk: [], traffic: [] },
      resource_units: { ram: "GB", cpu: "core", disk: "GB", traffic: "GB" },
    },
    ...overrides,
  };
}

afterEach(() => {
  getPlansPage.mockReset();
  vi.restoreAllMocks();
});

describe("PlanCatalog", () => {
  it("refreshes only the plan results when paginating", async () => {
    const scrollTo = vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    getPlansPage.mockResolvedValue(
      page({ plans: [plan(2, "Plan two")], page: 2 }),
    );
    const user = userEvent.setup();

    render(<PlanCatalog plansPage={page()} />);
    expect(screen.getByText("Plan one")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: strings.nextPage }));

    await waitFor(() => expect(screen.getByText("Plan two")).toBeInTheDocument());
    expect(screen.queryByText("Plan one")).not.toBeInTheDocument();
    expect(getPlansPage).toHaveBeenCalledWith(
      expect.objectContaining({ page: "2", page_size: "1" }),
    );
    expect(scrollTo).not.toHaveBeenCalled();
  });

  it("exposes filters, toolbar, cards, empty state, and footer as render props", () => {
    render(
      <PlanCatalog
        emptyState={({ hasActiveFilters }) => (
          <div>{hasActiveFilters ? "filtered empty" : "plain empty"}</div>
        )}
        filters={({ actions }) => (
          <aside>
            <button type="button" onClick={actions.onReset}>custom reset</button>
          </aside>
        )}
        footer={({ onReset }) => (
          <button type="button" onClick={onReset}>custom footer reset</button>
        )}
        plansPage={page({ plans: [] })}
        renderPlan={(item) => <article key={item.id}>{item.company_name}</article>}
        toolbar={({ data }) => <div>custom toolbar {data.count}</div>}
      />,
    );

    expect(screen.getByRole("button", { name: "custom reset" })).toBeInTheDocument();
    expect(screen.getByText("custom toolbar 2")).toBeInTheDocument();
    expect(screen.getByText("plain empty")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "custom footer reset" })).toBeInTheDocument();
  });

  it("renders custom plan cards and hides pagination when requested", () => {
    render(
      <PlanCatalog
        plansPage={page()}
        renderPlan={(item) => <article key={item.id}>custom {item.company_name}</article>}
        showPagination={false}
      />,
    );

    expect(screen.getByText("custom Host 1")).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: strings.paginationLabel })).not.toBeInTheDocument();
  });

  it("shows every resource filter on the all tab", async () => {
    const user = userEvent.setup();
    render(<PlanCatalog plansPage={page({ plans: [], count: 0 })} />);

    await user.click(screen.getByRole("button", { name: strings.filtersLabel }));

    expect(screen.getByText(strings.resourceRam)).toBeInTheDocument();
    expect(screen.getByText(strings.resourceCpu)).toBeInTheDocument();
    expect(screen.getByText(strings.resourceDisk)).toBeInTheDocument();
    expect(screen.getByText(strings.resourceTraffic)).toBeInTheDocument();
  });

  it("labels resource filter options with meaningful units", async () => {
    const user = userEvent.setup();
    render(
      <PlanCatalog
        plansPage={page({
          plans: [],
          count: 0,
          facets: {
            companies: [],
            operating_systems: [],
            locations: [],
            resources: { ram: [], cpu: [], disk: [1024], traffic: [] },
            resource_units: { ram: "GB", cpu: "core", disk: "GB", traffic: "GB" },
          },
        })}
      />,
    );

    await user.click(screen.getByRole("button", { name: strings.filtersLabel }));
    await user.click(screen.getByRole("button", { name: strings.resourceDisk }));
    expect(screen.getByText(new RegExp(strings.unitTB))).toBeInTheDocument();
  });

  it("renders plan-card skeletons while loading", () => {
    render(<PlanCatalog loading plansPage={page()} />);

    expect(screen.getByTestId("plan-catalog-skeleton")).toBeInTheDocument();
    expect(screen.queryByText("Plan one")).not.toBeInTheDocument();
  });
});
