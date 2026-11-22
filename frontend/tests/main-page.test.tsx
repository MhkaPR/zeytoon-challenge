import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CompanyCard } from "@/src/features/company/CompanyCard";
import { SearchBox } from "@/src/features/home/SearchBox";
import { MainBody } from "@/src/features/home/MainBody";
import { DEFAULT_SITE_CONFIG } from "@/src/lib/config/siteConfig";
import { strings } from "./messages";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/",
}));

vi.mock("@/src/features/home/HomeFooter", () => ({
  HomeFooter: () => null,
}));

afterEach(() => {
  vi.restoreAllMocks();
});

describe("MainBody", () => {
  it("renders the hero, service categories, and reference sections", () => {
    render(
      <MainBody
        plansPage={{
          plans: [],
          count: 0,
          page: 1,
          pageSize: 8,
          totalPages: 1,
          facets: {
            companies: [],
            operating_systems: [],
            locations: [],
            resources: { ram: [], cpu: [], disk: [], traffic: [] },
            resource_units: { ram: "GB", cpu: "core", disk: "GB", traffic: "GB" },
          },
        }}
        suggestedPlans={[]}
        recentCompanies={[
          {
            domain: "example.com",
            company_name: "Example Hosting",
            created_at: "2026-05-10T12:00:00Z",
          },
        ]}
        searchParams={{}}
        siteConfig={DEFAULT_SITE_CONFIG}
      />,
    );
    expect(screen.getByRole("search")).toBeInTheDocument();
    // The two primary calls to action sit under the search box.
    expect(screen.getAllByRole("link", { name: strings.ctaViewCompanies }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: strings.ctaViewHosts }).length).toBeGreaterThan(0);
    expect(document.getElementById("pricing")).toBeInTheDocument();
    expect(document.getElementById("providers")).toBeInTheDocument();
    expect(document.getElementById("steps")).toBeInTheDocument();
    expect(screen.getByText("۵/۱۰")).toBeInTheDocument();
  });
});

describe("SearchBox", () => {
  it("has an accessible search field", () => {
    render(<SearchBox />);
    expect(screen.getByRole("searchbox")).toBeInTheDocument();
  });
});

describe("CompanyCard", () => {
  it("links to the company page and shows the plan count", () => {
    render(<CompanyCard name="Example Hosting" domain="example.com" planCount={2} />);
    expect(screen.getByText("Example Hosting")).toBeInTheDocument();
    expect(screen.getByText("example.com")).toBeInTheDocument();
    expect(screen.getByText(strings.viewCompany)).toBeInTheDocument();
  });
});
