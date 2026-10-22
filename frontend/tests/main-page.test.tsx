import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CompanyCard } from "@/src/components/CompanyCard";
import { FilterBox, EMPTY_FILTERS } from "@/src/features/home/FilterBox";
import { SearchBox } from "@/src/features/home/SearchBox";
import { MainBody } from "@/src/features/home/MainBody";
import { strings } from "@/src/lib/i18n/strings";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/",
}));

afterEach(() => {
  vi.restoreAllMocks();
});

describe("MainBody", () => {
  it("renders the search box, service chips, and filter box", () => {
    render(<MainBody />);
    expect(screen.getByRole("search")).toBeInTheDocument();
    // Four service-type chips, host active by default.
    expect(screen.getByRole("button", { name: strings.serviceHost })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    for (const label of [
      strings.serviceVirtualServer,
      strings.serviceDedicatedServer,
      strings.serviceCdn,
    ]) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }
    expect(screen.getByLabelText(strings.serverLocationLabel)).toBeInTheDocument();
  });

  it("shows only a traffic chooser for the CDN service type", async () => {
    const user = userEvent.setup();
    render(<MainBody />);
    await user.click(screen.getByRole("button", { name: strings.serviceCdn }));
    expect(screen.getByLabelText(strings.resourceTraffic)).toBeInTheDocument();
    expect(screen.queryByLabelText(strings.resourceRam)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(strings.resourceCpu)).not.toBeInTheDocument();
  });
});

describe("SearchBox", () => {
  it("has an accessible search field", () => {
    render(<SearchBox />);
    expect(screen.getByRole("searchbox")).toBeInTheDocument();
  });
});

describe("FilterBox", () => {
  it("opens the price range field on demand", async () => {
    const user = userEvent.setup();
    render(
      <FilterBox serviceType="host" value={EMPTY_FILTERS} onChange={() => {}} />,
    );
    expect(screen.queryByLabelText(strings.priceFrom)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: new RegExp(strings.priceRangeLabel) }));
    expect(screen.getByLabelText(strings.priceFrom)).toBeInTheDocument();
    expect(screen.getByLabelText(strings.priceTo)).toBeInTheDocument();
  });
});

describe("CompanyCard", () => {
  it("links to the company page and shows the fallback description", () => {
    render(<CompanyCard name="Example Hosting" domain="example.com" />);
    expect(screen.getByText("Example Hosting")).toBeInTheDocument();
    expect(screen.getByText("example.com")).toBeInTheDocument();
    expect(screen.getByText(strings.companyCardFallback)).toBeInTheDocument();
  });
});
