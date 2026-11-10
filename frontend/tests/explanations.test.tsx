import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { explanationText, reasonSentence } from "@/src/features/home/explanationText";
import { SuggestedPlans } from "@/src/features/home/SuggestedPlans";
import type { ClusterExplanation, Reason } from "@/src/lib/api/explanations";
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

const t = Object.assign((key: string) => strings[key] ?? key, {
  raw: (key: string) => strings[key] ?? key,
});

describe("explanationText", () => {
  it("describes a textual match as a product category", () => {
    const text = reasonSentence(
      { feature: "textual_category", type: "textual", f1: 0.6 },
      t,
    );
    expect(text).toBe(strings.explainTextual);
    expect(/\d/.test(text)).toBe(false);
  });

  it("quotes a real-unit range for a numeric match", () => {
    const text = reasonSentence(
      { feature: "cpu", type: "numeric", f1: 0.8, real_range: [2, 4] },
      t,
    );
    expect(text).toContain("۲");
    expect(text).toContain("۴");
  });

  it("names a category for a categorical match", () => {
    const text = reasonSentence(
      { feature: "os", type: "categorical", f1: 0.7, label: "Linux" },
      t,
    );
    expect(text).toContain("Linux");
  });
});

describe("SuggestedPlans explanations", () => {
  const explanations: ClusterExplanation[] = [
    {
      cluster_id: 0,
      representative_plan_id: 1,
      reasons: [{ feature: "textual_category", type: "textual", f1: 0.6 }],
    },
  ];

  it("opens the reason modal from the badge", async () => {
    const user = userEvent.setup();
    render(
      <SuggestedPlans
        explanations={explanations}
        plans={[plan(1, "Cloud plan"), plan(2, "WordPress plan")]}
      />,
    );
    const badge = screen.getByRole("button", { name: strings.explainReasonLabel });
    expect(badge).toBeInTheDocument();
    await user.click(badge);
    expect(screen.getByText(strings.explainTextual)).toBeInTheDocument();
  });

  it("renders no reason when explanations are absent", () => {
    render(<SuggestedPlans plans={[plan(2, "WordPress plan")]} />);
    expect(
      screen.queryByRole("button", { name: strings.explainReasonLabel }),
    ).not.toBeInTheDocument();
  });
});

describe("explanationText join", () => {
  it("joins multiple reasons into one explanation", () => {
    const reasons: Reason[] = [
      { feature: "textual_category", type: "textual", f1: 0.6 },
      { feature: "ram", type: "numeric", f1: 0.8, real_range: [8, 16] },
    ];
    const text = explanationText(reasons, t);
    expect(text).toContain(strings.explainTextual);
    expect(text.length).toBeGreaterThan(strings.explainTextual.length);
  });
});
