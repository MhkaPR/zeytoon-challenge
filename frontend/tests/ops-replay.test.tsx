import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AlertsPanel } from "@/src/features/ops/replay/AlertsPanel";
import { FailureRateBadge } from "@/src/features/ops/replay/FailureRateBadge";
import { RecipientManager } from "@/src/features/ops/replay/RecipientManager";
import { ReplayRunsTable } from "@/src/features/ops/replay/ReplayRunsTable";
import type { FailureAlert, ReplayRun } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";

afterEach(() => {
  vi.restoreAllMocks();
});

const run: ReplayRun = {
  id: 51,
  link_id: 11,
  recipe_id: 5,
  state: "completed",
  before_trace_id: 1,
  after_trace_id: 2,
  diff_summary: { changed: 2, removed: 1 },
  diff_applied: true,
  stats_applied: 2,
  stats_skipped: 1,
  stats_failed: 0,
  failures: [],
  started_at: "2026-10-01T10:00:00Z",
  finished_at: "2026-10-01T10:01:00Z",
};

const alert: FailureAlert = {
  id: 61,
  link_id: 11,
  state: "open",
  failure_rate: 0.45,
  raised_at: "2026-10-01T10:02:00Z",
  resolved_at: null,
};

describe("replay and alerts", () => {
  it("renders before/after traces, diff summary, and stats", () => {
    render(<ReplayRunsTable runs={[run]} />);
    expect(screen.getByText('{"changed":2,"removed":1}')).toBeInTheDocument();
    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(screen.getByText("51 / 11")).toBeInTheDocument();
  });

  it("marks a failure rate above the threshold", () => {
    render(<FailureRateBadge rate={0.45} threshold={0.2} />);
    expect(screen.getByText(/45.0%/)).toBeInTheDocument();
    expect(screen.getByText(/20.0%/)).toBeInTheDocument();
  });

  it("re-runs a flagged link from the alerts panel", async () => {
    const onRerun = vi.fn();
    const user = userEvent.setup();
    render(
      <AlertsPanel alerts={[alert]} onRerun={onRerun} threshold={0.2} />,
    );
    expect(screen.getByText(/Link #11/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: opsStrings.rerun }));
    expect(onRerun).toHaveBeenCalledWith(11);
  });

  it("adds and deactivates recipients", async () => {
    const onAdd = vi.fn();
    const onDeactivate = vi.fn();
    const user = userEvent.setup();
    render(
      <RecipientManager
        onAdd={onAdd}
        onDeactivate={onDeactivate}
        recipients={[
          {
            id: 71,
            user_id: 9,
            name: "Ops",
            is_active: true,
            user_phone: "091***123",
          },
        ]}
      />,
    );

    expect(screen.getByText(opsStrings.inAppOnly)).toBeInTheDocument();
    await user.type(screen.getByLabelText(opsStrings.recipientUserId), "9");
    await user.type(screen.getByLabelText(opsStrings.recipientName), "Ops Team");
    await user.click(screen.getByRole("button", { name: opsStrings.addRecipient }));
    expect(onAdd).toHaveBeenCalledWith(9, "Ops Team");

    await user.click(screen.getByRole("button", { name: opsStrings.deactivate }));
    expect(onDeactivate).toHaveBeenCalledWith(71);
  });
});
