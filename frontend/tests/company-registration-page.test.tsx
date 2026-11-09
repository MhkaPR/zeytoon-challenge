import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
  usePathname: () => "/panel/new",
}));

import { CompanyRegistrationPage } from "@/src/features/company/CompanyRegistrationPage";
import { setAccessToken } from "@/src/lib/session";
import { strings } from "./messages";

afterEach(() => {
  vi.restoreAllMocks();
  push.mockClear();
  setAccessToken(null);
});

describe("company registration page", () => {
  it("explains the process, shows steps, and shows a panel button after submission", async () => {
    setAccessToken("tok");
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true, json: async () => ({ company: { id: 5 }, step_progress: [] }),
    })));
    const user = userEvent.setup();
    render(<CompanyRegistrationPage />);

    expect(screen.getByText(strings.registerCompanyTitle)).toBeInTheDocument();
    expect(screen.getByText(strings.registerCompanyStepsTitle)).toBeInTheDocument();
    expect(screen.getByText(strings.stepCompanyInfo)).toBeInTheDocument();
    expect(screen.getByText(strings.stepVerification)).toBeInTheDocument();

    await user.type(screen.getByLabelText(strings.companyDomain), "example.com");
    await user.type(screen.getByLabelText(strings.companyName), "Example");
    await user.type(screen.getByLabelText(strings.representativeName), "Ali");
    await user.type(screen.getByLabelText(strings.companyPhone), "02123456789");
    await user.click(screen.getByRole("button", { name: strings.submitCompany }));

    const panelBtn = await screen.findByRole("button", { name: strings.goToCompaniesPanel });
    await user.click(panelBtn);
    expect(push).toHaveBeenCalledWith("/panel");
  });
});
