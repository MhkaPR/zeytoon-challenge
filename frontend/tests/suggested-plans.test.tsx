import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SuggestedPlans } from "@/src/features/home/SuggestedPlans";
import type { PublicPlan } from "@/src/lib/api/publicCatalog";
import { strings } from "./messages";

function plan(id: number, name: string): PublicPlan {
  return {
    id,
    domain: `host-${id}.example`,
    company_name: `Host ${id}`,
    plan_type: "hosting",
    values: { plan_name: name, price_amount: 100000 },
    published_at: null,
  };
}

describe("SuggestedPlans", () => {
  it("renders a horizontal list of suggested plans", () => {
    render(
      <SuggestedPlans
        plans={[plan(1, "Cloud plan"), plan(2, "WordPress plan")]}
      />,
    );

    expect(screen.getByText(strings.suggestedTitle)).toBeInTheDocument();
    expect(screen.getByText(strings.suggestedIntro)).toBeInTheDocument();
    const list = screen.getByRole("list", { name: strings.suggestedTitle });
    expect(list).toBeInTheDocument();
    expect(screen.getByText("Cloud plan")).toBeInTheDocument();
    expect(screen.getByText("WordPress plan")).toBeInTheDocument();
  });

  it("renders nothing when there are no suggestions", () => {
    const { container } = render(<SuggestedPlans plans={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
