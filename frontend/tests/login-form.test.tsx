import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LoginForm } from "@/src/features/auth/LoginForm";

afterEach(() => {
  vi.restoreAllMocks();
});

function mockFetchSequence(responses: Array<{ ok: boolean; body: unknown }>) {
  const fetchMock = vi.fn();
  for (const response of responses) {
    fetchMock.mockResolvedValueOnce({
      ok: response.ok,
      status: response.ok ? 200 : 400,
      json: async () => response.body,
    });
  }
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("LoginForm", () => {
  it("requests a code and shows the expiry countdown", async () => {
    mockFetchSequence([
      { ok: true, body: { status: "sent", expires_in_seconds: 120 } },
    ]);
    render(<LoginForm />);

    await userEvent.type(screen.getByLabelText(/phone number/i), "+989123456789");
    await userEvent.click(screen.getByRole("button", { name: /send code/i }));

    await waitFor(() =>
      expect(screen.getByLabelText("countdown")).toHaveTextContent(/2:00/),
    );
  });

  it('shows the "The code is incorrect" message for a wrong or expired code', async () => {
    mockFetchSequence([
      { ok: true, body: { status: "sent", expires_in_seconds: 120 } },
      {
        ok: false,
        body: {
          error: { code: "otp_incorrect", message: "The code is incorrect" },
        },
      },
    ]);
    render(<LoginForm />);

    await userEvent.type(screen.getByLabelText(/phone number/i), "+989123456789");
    await userEvent.click(screen.getByRole("button", { name: /send code/i }));
    await waitFor(() => expect(screen.getByLabelText("countdown")).toBeInTheDocument());

    await userEvent.type(screen.getByLabelText(/enter the code/i), "000000");
    await userEvent.click(screen.getByRole("button", { name: /log in/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("The code is incorrect"),
    );
    expect(screen.getByRole("alert")).not.toHaveTextContent(/expire/i);
  });
});
