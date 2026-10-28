import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LinkReviewTable } from "@/src/features/ops/links/LinkReviewTable";
import { SiteOnboarding } from "@/src/features/ops/sites/SiteOnboarding";
import type { Link, Site } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";

afterEach(() => {
  vi.restoreAllMocks();
});

const site: Site = {
  id: 4,
  company_id: 7,
  domain: "example.com",
  has_sitemap: true,
  sitemap_url: "https://example.com/sitemap.xml",
  maintenance_state: "onboarding",
  onboarded_at: null,
};

const links: Link[] = [
  {
    id: 11,
    site_id: 4,
    url: "https://example.com/plans",
    source: "sitemap",
    review_state: "candidate",
    pipeline_stage: "review",
    failure_rate: 0,
    current_trace_id: null,
  },
  {
    id: 12,
    site_id: 4,
    url: "https://example.com/about",
    source: "manual",
    review_state: "candidate",
    pipeline_stage: "review",
    failure_rate: 0,
    current_trace_id: null,
  },
];

describe("site onboarding", () => {
  it("discovers links when the site has a sitemap", async () => {
    const onDiscover = vi.fn();
    const user = userEvent.setup();
    render(
      <SiteOnboarding
        linksCount={0}
        onDiscover={onDiscover}
        onManualAdd={vi.fn()}
        site={site}
      />,
    );

    expect(screen.getByText(opsStrings.sitemapFound)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: new RegExp(opsStrings.discoverLinks) }));
    expect(onDiscover).toHaveBeenCalled();
  });

  it("accepts manual links when no sitemap exists", async () => {
    const onManualAdd = vi.fn();
    const user = userEvent.setup();
    render(
      <SiteOnboarding
        linksCount={0}
        onDiscover={vi.fn()}
        onManualAdd={onManualAdd}
        site={{ ...site, has_sitemap: false, sitemap_url: "" }}
      />,
    );

    expect(screen.getByText(opsStrings.sitemapMissing)).toBeInTheDocument();
    await user.type(
      screen.getByLabelText(opsStrings.manualLinksTitle),
      "https://example.com/a{enter}https://example.com/b",
    );
    await user.click(screen.getByRole("button", { name: opsStrings.addLinks }));
    expect(onManualAdd).toHaveBeenCalledWith([
      "https://example.com/a",
      "https://example.com/b",
    ]);
  });

  it("keeps the rest and submits removed links", async () => {
    const onReview = vi.fn();
    const user = userEvent.setup();
    render(<LinkReviewTable links={links} onReview={onReview} />);

    const removeButtons = screen.getAllByRole("button", { name: opsStrings.remove });
    await user.click(removeButtons[1]);
    await user.click(screen.getByRole("button", { name: opsStrings.reviewSubmit }));

    expect(onReview).toHaveBeenCalledWith([11], [12]);
  });
});
