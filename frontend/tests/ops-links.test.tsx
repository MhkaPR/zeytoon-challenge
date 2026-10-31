import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SiteOnboarding } from "@/src/features/ops/sites/SiteOnboarding";
import type { Site } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";
import { LinkList } from "@/src/features/ops/links/LinkList";
import { rerunLink } from "@/src/lib/api/ops";

vi.mock("@/src/lib/session", () => ({ getAccessToken: () => "token" }));
vi.mock("@/src/lib/api/ops", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/src/lib/api/ops")>();
  return { ...actual, rerunLink: vi.fn() };
});

afterEach(() => {
  vi.restoreAllMocks();
});

const site: Site = {
  id: 4,
  company_id: 7,
  domain: "example.com",
  maintenance_state: "onboarding",
  onboarded_at: null,
};

describe("automated site pipeline", () => {
  it("shows pipeline progress without manual discovery or link actions", () => {
    render(<SiteOnboarding linksCount={2} site={site} />);

    expect(screen.getByText(opsStrings.automaticPipelineHint)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("allows retrying a second link while the first retry is queued", async () => {
    const user = userEvent.setup();
    let resolveFirst: (() => void) | undefined;
    let resolveSecond: (() => void) | undefined;
    vi.mocked(rerunLink)
      .mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = () => resolve({} as never); }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveSecond = () => resolve({} as never); }));
    render(
      <LinkList
        links={[1, 2].map((id) => ({
          id,
          site_id: 4,
          url: `https://example.com/${id}`,
          source: "manual",
          review_state: "kept",
          pipeline_stage: "classified",
          failure_rate: 0,
          current_trace_id: 12,
          last_error: "plan_extraction: no valid plans",
        }))}
      />,
    );

    const retryButtons = screen.getAllByRole("button", { name: opsStrings.retry });
    await user.click(retryButtons[0]);
    await user.click(retryButtons[1]);

    expect(rerunLink).toHaveBeenCalledTimes(2);
    await act(async () => {
      resolveFirst?.();
      resolveSecond?.();
    });
  });

  it("explains an empty quality result without showing a pipeline error", () => {
    render(
      <LinkList
        links={[{
          id: 3,
          site_id: 4,
          url: "https://example.com/no-price",
          source: "manual",
          review_state: "kept",
          pipeline_stage: "classified",
          failure_rate: 0,
          current_trace_id: 12,
          last_error: "no_valid_plans: no plan met the quality gate",
          pipeline_task_state: "completed",
        }]}
      />,
    );

    expect(screen.getByText(opsStrings.noValidPlansOutcome)).toBeInTheDocument();
    expect(screen.queryByText(opsStrings.pipelineFailure)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: opsStrings.retry })).toBeEnabled();
  });
});
