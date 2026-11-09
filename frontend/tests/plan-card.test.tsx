import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { PlanCard } from "@/src/features/home/planCatalog/PlanCard";
import type { PublicPlan } from "@/src/lib/api/publicCatalog";
import { strings } from "./messages";

const plan: PublicPlan = {
  id: 7,
  domain: "example.com",
  company_name: "Example Host",
  plan_type: "hosting",
  values: {
    plan_name: "Business Plan",
    price_amount: 250000,
    ram_amount: 8,
    ram_unit: "GB",
    storage_amount: 1,
    storage_unit: "TB",
    other: [
      { key: "backup", value: "daily" },
      { label: "Control panel", value: "cPanel" },
      { name: "Datacenter", value: { city: "Tehran", country: "Iran" } },
      "Free SSL",
    ],
  },
  published_at: null,
};

describe("PlanCard", () => {
  it("opens a details modal with the plan specifications", async () => {
    const user = userEvent.setup();
    render(<PlanCard plan={plan} />);

    await user.click(screen.getByRole("button", { name: strings.viewPlanDetails }));

    const dialog = screen.getByRole("dialog", { name: strings.planDetailsTitle });
    expect(within(dialog).getByText("Business Plan")).toBeInTheDocument();
    expect(within(dialog).getByText("Example Host · example.com")).toBeInTheDocument();
    expect(within(dialog).getByText("8 GB")).toBeInTheDocument();
    expect(within(dialog).getByText("1 TB")).toBeInTheDocument();
  });

  it("renders the other attributes in a separate readable section", async () => {
    const user = userEvent.setup();
    render(<PlanCard plan={plan} />);

    await user.click(screen.getByRole("button", { name: strings.viewPlanDetails }));

    const dialog = screen.getByRole("dialog", { name: strings.planDetailsTitle });
    const section = within(dialog).getByRole("region", {
      name: strings.otherAttributes,
    });
    expect(within(section).getByText("backup")).toBeInTheDocument();
    expect(within(section).getByText("daily")).toBeInTheDocument();
    expect(within(section).getByText("Control panel")).toBeInTheDocument();
    expect(within(section).getByText("cPanel")).toBeInTheDocument();
    expect(within(section).getByText("Datacenter")).toBeInTheDocument();
    expect(within(section).getByText("city: Tehran، country: Iran")).toBeInTheDocument();
    expect(within(section).getByText("Free SSL")).toBeInTheDocument();
    expect(within(dialog).queryByText(/\[object Object\]/)).not.toBeInTheDocument();
  });
});
