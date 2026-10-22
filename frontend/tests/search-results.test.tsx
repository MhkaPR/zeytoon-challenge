import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CompanyCard } from "@/src/features/company/CompanyCard";
import { ResultsList } from "@/src/features/search/ResultsList";
import { SEARCH_INDEX, SERVICE_TYPES, suggest } from "@/src/features/search/data";
import { strings } from "@/src/lib/i18n/strings";

describe("search data", () => {
  it("exposes the four service-type chips", () => {
    expect(SERVICE_TYPES.map((type) => type.label)).toEqual([
      strings.serviceHost,
      strings.serviceVirtualServer,
      strings.serviceDedicatedServer,
      strings.serviceCdn,
    ]);
  });

  it("suggests matches and honours the service filter", () => {
    const all = suggest("سرور");
    expect(all.length).toBeGreaterThan(0);
    const cdnOnly = suggest("شبکه", "cdn");
    expect(cdnOnly.every((result) => result.service === "cdn")).toBe(true);
    expect(suggest("", "host")).toEqual([]);
  });
});

describe("ResultsList", () => {
  it("renders one list item per result", () => {
    const { container } = render(<ResultsList results={SEARCH_INDEX.slice(0, 3)} />);
    expect(container.querySelectorAll('[role="option"]')).toHaveLength(3);
  });

  it("shows the empty message when there are no results", () => {
    const { container } = render(<ResultsList results={[]} />);
    expect(container.textContent).toContain(strings.noResults);
  });
});

describe("CompanyCard", () => {
  it("renders the company name, domain, and fallback description", () => {
    const { container, getByText } = render(
      <CompanyCard name="Example Hosting" domain="example.com" />,
    );
    expect(getByText("Example Hosting")).toBeInTheDocument();
    expect(getByText("example.com")).toBeInTheDocument();
    expect(container.textContent).toContain(strings.companyCardFallback);
  });
});
