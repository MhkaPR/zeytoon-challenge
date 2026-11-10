import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SuggestedPlans } from "@/src/features/home/SuggestedPlans";
import type { ClusterIntentExplanation } from "@/src/lib/api/intentExplanations";
import type { PublicPlan } from "@/src/lib/api/publicCatalog";

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

const explanations: ClusterIntentExplanation[] = [
  {
    cluster_id: 0,
    representative_plan_id: 1,
    plan_ids: [1],
    intent: "value",
    direction: "positive",
    message: "دنبال بهترین نسبت امکانات به قیمت هستی؟",
    confidence: { lift: 4.2, p: 0.001, mcc: 0.62 },
  },
  {
    cluster_id: 1,
    representative_plan_id: 2,
    plan_ids: [2],
    intent: "value",
    direction: "positive",
    message: "دنبال بهترین نسبت امکانات به قیمت هستی؟",
    confidence: { lift: 3.1, p: 0.002, mcc: 0.51 },
  },
  {
    cluster_id: 2,
    representative_plan_id: 3,
    plan_ids: [3],
    intent: "cheap",
    direction: "positive",
    message: "دنبال گزینه‌های اقتصادی با قیمت پایین هستی؟",
    confidence: { lift: 2.5, p: 0.01, mcc: 0.4 },
  },
];

describe("SuggestedPlans intent explanations", () => {
  it("renders one row per explanation with its own plan list", () => {
    render(
      <SuggestedPlans
        explanations={explanations}
        plans={[
          plan(1, "Value One"),
          plan(2, "Value Two"),
          plan(3, "Cheap One"),
        ]}
      />,
    );

    expect(
      screen.getAllByText("دنبال بهترین نسبت امکانات به قیمت هستی؟"),
    ).toHaveLength(2);
    expect(
      screen.getByText("دنبال گزینه‌های اقتصادی با قیمت پایین هستی؟"),
    ).toBeInTheDocument();
    expect(screen.getByText("Value One")).toBeInTheDocument();
    expect(screen.getByText("Value Two")).toBeInTheDocument();
    expect(screen.getByText("Cheap One")).toBeInTheDocument();
  });

  it("falls back to the flat plan list when explanations are absent", () => {
    render(<SuggestedPlans plans={[plan(4, "Fallback Plan")]} />);
    expect(screen.getByText("Fallback Plan")).toBeInTheDocument();
  });

  it("does not display exploring explanations or their plans", () => {
    render(
      <SuggestedPlans
        explanations={[
          {
            cluster_id: 3,
            representative_plan_id: 5,
            plan_ids: [5],
            intent: "exploring",
            direction: null,
            message: "در حال کاوش گزینه‌های مختلف هستی؟",
            confidence: null,
          },
        ]}
        plans={[plan(5, "Exploring Plan")]}
      />,
    );

    expect(
      screen.queryByText("در حال کاوش گزینه‌های مختلف هستی؟"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Exploring Plan")).not.toBeInTheDocument();
  });
});
