import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CompanyCard } from "@/src/features/company/CompanyCard";
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
  it("renders the hero, service categories, and reference sections", () => {
    render(<MainBody />);
    expect(screen.getByRole("search")).toBeInTheDocument();
    // Four service-type chips, host selected by default. HeroUI renders the single-select
    // ToggleButtonGroup as a radiogroup, so the active chip is the checked radio.
    expect(screen.getByRole("radio", { name: strings.serviceHost })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    for (const label of [
      strings.serviceVirtualServer,
      strings.serviceDedicatedServer,
      strings.serviceCdn,
    ]) {
      expect(screen.getByRole("radio", { name: label })).toBeInTheDocument();
    }
    expect(document.getElementById("pricing")).toBeInTheDocument();
    expect(document.getElementById("providers")).toBeInTheDocument();
    expect(document.getElementById("steps")).toBeInTheDocument();
  });
});

describe("SearchBox", () => {
  it("has an accessible search field", () => {
    render(<SearchBox />);
    expect(screen.getByRole("searchbox")).toBeInTheDocument();
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
