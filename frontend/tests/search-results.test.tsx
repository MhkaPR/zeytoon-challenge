import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CompanyCard } from "@/src/features/company/CompanyCard";
import { ResultsList } from "@/src/features/search/ResultsList";
import { SERVICE_TYPES, searchIndexFrom, suggest } from "@/src/features/search/data";
import fa from "@/src/lib/i18n/messages/fa.json";
import { strings } from "./messages";

const searchIndex = searchIndexFrom((fa as Record<string, unknown>).searchIndex);

describe("search data", () => {
  it("exposes the four service-type chips", () => {
    expect(SERVICE_TYPES.map((type) => strings[type.labelKey])).toEqual([
      strings.serviceHost,
      strings.serviceVirtualServer,
      strings.serviceDedicatedServer,
      strings.serviceCdn,
    ]);
  });

  it("suggests matches and honours the service filter", () => {
    const all = suggest(searchIndex, "سرور");
    expect(all.length).toBeGreaterThan(0);
    const cdnOnly = suggest(searchIndex, "شبکه", "cdn");
    expect(cdnOnly.every((result) => result.service === "cdn")).toBe(true);
    expect(suggest(searchIndex, "", "host")).toEqual([]);
  });
});

describe("ResultsList", () => {
  it("renders one list item per result", () => {
    const { container } = render(<ResultsList results={searchIndex.slice(0, 3)} />);
    expect(container.querySelectorAll('[role="option"]')).toHaveLength(3);
  });

  it("shows the empty message when there are no results", () => {
    const { container } = render(<ResultsList results={[]} />);
    expect(container.textContent).toContain(strings.noResults);
  });
});

describe("CompanyCard", () => {
  it("renders the company name, domain, plan count, and company action", () => {
    const { container, getByText } = render(
      <CompanyCard name="Example Hosting" domain="example.com" planCount={3} />,
    );
    expect(getByText("Example Hosting")).toBeInTheDocument();
    expect(getByText("example.com")).toBeInTheDocument();
    expect(container.textContent).toContain("طرح منتشرشده");
    expect(getByText(strings.viewCompany)).toBeInTheDocument();
  });
});
