import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApprovalQueue } from "@/src/features/ops/approvals/ApprovalQueue";
import { CompanyReviewCard } from "@/src/features/ops/approvals/CompanyReviewCard";
import type { ApprovalQueueEntry } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";

afterEach(() => {
  vi.restoreAllMocks();
});

const entry: ApprovalQueueEntry = {
  company_id: 7,
  company_name: "Example Hosting",
  representative_name: "Ali Rezaei",
  domain: "example.com",
  phone_masked: "021***789",
  registered_at: "2026-10-01T10:00:00Z",
  duplicate_domain_warning: true,
  duplicate_of: [3],
};

describe("approval queue", () => {
  it("shows the duplicate-domain warning without auto-resolving it", () => {
    render(<ApprovalQueue entries={[entry]} onDecision={vi.fn()} />);

    expect(screen.getByText(opsStrings.duplicateWarning)).toBeInTheDocument();
    expect(screen.getByText(/3/)).toBeInTheDocument();
    expect(screen.getByText("Example Hosting")).toBeInTheDocument();
    expect(screen.getByText("Ali Rezaei")).toBeInTheDocument();
  });

  it("records approval with the operator note", async () => {
    const onDecision = vi.fn();
    const user = userEvent.setup();
    render(<CompanyReviewCard entry={entry} onDecision={onDecision} />);

    await user.type(screen.getByLabelText(opsStrings.decisionNote), "checked domain");
    await user.click(screen.getByRole("button", { name: opsStrings.approve }));

    expect(onDecision).toHaveBeenCalledWith(7, "approved", "checked domain");
  });

  it("records a not-approved outcome separately", async () => {
    const onDecision = vi.fn();
    const user = userEvent.setup();
    render(<CompanyReviewCard entry={entry} onDecision={onDecision} />);

    await user.click(screen.getByRole("button", { name: opsStrings.reject }));

    expect(onDecision).toHaveBeenCalledWith(7, "not_approved", "");
  });

  it("shows the empty queue state", () => {
    render(<ApprovalQueue entries={[]} onDecision={vi.fn()} />);
    expect(screen.getByText(opsStrings.approvalsEmpty)).toBeInTheDocument();
  });
});
