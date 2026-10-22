import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ContinueRegistration } from "@/src/features/company/ContinueRegistration";
import { CompanySwitcher } from "@/src/features/panel/CompanySwitcher";
import { EmptyState } from "@/src/features/panel/EmptyState";
import { strings } from "@/src/lib/i18n/strings";
import type { Company } from "@/src/lib/api/companies";

afterEach(() => {
  vi.restoreAllMocks();
});

const company: Company = {
  id: 7,
  domain: "example.com",
  company_name: "Example Hosting",
  representative_name: "Ali Rezaei",
  phone_number: "02123456789",
  internal_number: "",
  verification_status: "pending",
  charge_status: "not_charged",
  crawl_enabled: false,
  is_archived: false,
  unverified: true,
};

describe("EmptyState", () => {
  it("shows the register button when the user owns no companies", () => {
    render(<EmptyState />);
    expect(
      screen.getByRole("button", { name: strings.registerNewCompany }),
    ).toBeInTheDocument();
  });
});

describe("CompanySwitcher", () => {
  it("renders one entry per company with its status", () => {
    render(
      <CompanySwitcher
        companies={[
          {
            id: 1,
            company_name: "Verified Co",
            verification_status: "verified",
            unverified: false,
          },
          {
            id: 2,
            company_name: "Pending Co",
            verification_status: "pending",
            unverified: true,
          },
        ]}
        activeId={2}
      />,
    );
    expect(screen.getByText("Verified Co")).toBeInTheDocument();
    expect(screen.getByText("Pending Co")).toBeInTheDocument();
    expect(screen.getByText(strings.pendingStatus)).toBeInTheDocument();
  });
});

describe("ContinueRegistration", () => {
  it("marks done and pending steps and offers the current step", () => {
    render(
      <ContinueRegistration
        company={company}
        steps={[
          { step_key: "company_information", order: 1, state: "approved", completed: true },
          { step_key: "verification", order: 2, state: "locked", completed: false },
        ]}
        currentStep="verification"
      />,
    );
    expect(screen.getByText(strings.stepDone)).toBeInTheDocument();
    expect(screen.getByText(strings.stepLocked)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: strings.goToCurrentStep }),
    ).toBeInTheDocument();
  });
});
