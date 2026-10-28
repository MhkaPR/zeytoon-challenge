import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TunablesForm } from "@/src/features/ops/settings/TunablesForm";
import { TableList } from "@/src/features/ops/tables/TableList";
import { opsStrings } from "@/src/lib/i18n/strings";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("settings", () => {
  it("toggles LLM labeling and saves runtime tunables", async () => {
    const onSave = vi.fn();
    const user = userEvent.setup();
    render(
      <TunablesForm
        onSave={onSave}
        values={{
          REPLAY_PERIOD_HOURS: 24,
          FAILURE_RATE_THRESHOLD: 0.2,
          FAILURE_RATE_WINDOW_RUNS: 5,
          LABELING_ENABLED: false,
          CLEANING_RULES: '{"price": "number"}',
        }}
      />,
    );

    await user.click(screen.getByRole("switch"));
    await user.click(screen.getByRole("button", { name: opsStrings.saveSettings }));

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        LABELING_ENABLED: true,
        CLEANING_RULES: { price: "number" },
      }),
    );
  });

  it("shows the disabled labeling state without blocking other stages", () => {
    render(
      <TableList
        labelingEnabled={false}
        onExtract={vi.fn()}
        onLabel={vi.fn()}
        stage="extracted"
        tables={[]}
        traceStored
      />,
    );
    expect(screen.getByText(new RegExp(opsStrings.labelingDisabled))).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: opsStrings.runLabeling }),
    ).toBeDisabled();
  });
});
