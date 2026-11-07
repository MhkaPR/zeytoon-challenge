import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PlanCard } from "@/src/features/home/planCatalog/PlanCard";
import type { PublicPlan } from "@/src/lib/api/publicCatalog";
import { strings } from "./messages";

const plan: PublicPlan = {
  id: 7,
  domain: "example.com",
  company_name: "Example Host",
  plan_type: "hosting",
  values: { plan_name: "Business Plan", price_amount: 250000 },
  url: "https://example.com/plans/7",
  published_at: null,
};

afterEach(() => vi.unstubAllGlobals());

describe("PlanCard interest signals", () => {
  it("sends a destination_visit signal when the plan page link is pressed", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<PlanCard plan={plan} />);

    await user.click(screen.getByRole("button", { name: strings.viewPlanPage }));

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/recommendations/signals"),
      expect.objectContaining({
        body: JSON.stringify({ kind: "destination_visit", plan_ids: [7] }),
      }),
    );
  });

  it("sends a details_view signal when the details button is pressed", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<PlanCard plan={plan} />);

    await user.click(screen.getByRole("button", { name: strings.viewPlanDetails }));

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/recommendations/signals"),
      expect.objectContaining({
        body: JSON.stringify({ kind: "details_view", plan_ids: [7] }),
      }),
    );
  });
});
