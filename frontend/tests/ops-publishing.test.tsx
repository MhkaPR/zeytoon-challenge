import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CleaningPanel } from "@/src/features/ops/publishing/CleaningPanel";
import type { CleaningResult } from "@/src/lib/api/ops";
import { opsStrings } from "./messages";

afterEach(() => {
  vi.restoreAllMocks();
});

const cleaning: CleaningResult = {
  link_id: 11,
  plan_type: "hosting",
  recipe_id: 5,
  cleaned_records: 2,
  exception_count: 1,
  records: [
    {
      natural_key: "basic",
      plan_type: "hosting",
      values: { name: "Basic", price: 120000 },
      exceptions: {},
    },
    {
      natural_key: "pro",
      plan_type: "hosting",
      values: { name: "Pro", price: "unknown" },
      exceptions: { price: "unit_unrecognized" },
    },
  ],
};

describe("cleaning and publishing", () => {
  it("surfaces only the resolvable exceptions and publishes", async () => {
    const onPublish = vi.fn();
    const user = userEvent.setup();
    render(
      <CleaningPanel
        cleaning={cleaning}
        onClean={vi.fn()}
        onPublish={onPublish}
        published={null}
        recipeReady
        stage="cleaned"
      />,
    );

    expect(screen.getByText(/price: unit_unrecognized/)).toBeInTheDocument();
    expect(screen.getByText(/2/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: opsStrings.runPublish }));
    expect(onPublish).toHaveBeenCalled();
  });

  it("blocks cleaning and publishing until the recipe is complete", () => {
    render(
      <CleaningPanel
        cleaning={null}
        onClean={vi.fn()}
        onPublish={vi.fn()}
        published={null}
        recipeReady={false}
        stage="mapped"
      />,
    );
    expect(screen.getByText(opsStrings.mapFirst)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: opsStrings.runCleaning }),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: opsStrings.runPublish }),
    ).toBeDisabled();
  });
});
