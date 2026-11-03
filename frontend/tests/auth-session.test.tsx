import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/",
}));

import { LoginDialogProvider } from "@/src/features/auth/LoginDialog";
import { SessionProvider } from "@/src/features/auth/SessionProvider";
import { Header } from "@/src/features/site/Header";
import { strings } from "./messages";
import { setAccessToken } from "@/src/lib/session";

afterEach(() => {
  vi.restoreAllMocks();
  setAccessToken(null);
});

// A faithful mini-backend: /session is authenticated ONLY when the Bearer header matches the
// token issued at verify time (mirrors backend/src/accounts/selectors.py).
function backend() {
  let issuedToken: string | null = null;
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const u = String(url);
    const auth = (init?.headers as Record<string, string> | undefined)?.Authorization;
    if (u.includes("/auth/session")) {
      const ok = issuedToken !== null && auth === `Bearer ${issuedToken}`;
      return {
        ok: true,
        json: async () =>
          ok
            ? { authenticated: true, user: { phone: "+989123456789", role: "regular" } }
            : { authenticated: false, role: "guest" },
      };
    }
    if (u.includes("/auth/otp/request"))
      return { ok: true, json: async () => ({ status: "sent", expires_in_seconds: 120 }) };
    if (u.includes("/auth/otp/verify")) {
      issuedToken = "tok-123";
      return {
        ok: true,
        json: async () => ({
          access_token: issuedToken,
          token_type: "Bearer",
          expires_in: 60,
          redirect_to: "/",
          user: { phone: "+989123456789", role: "regular" },
        }),
      };
    }
    if (u.includes("/auth/token/refresh")) return { ok: false, status: 401, json: async () => ({}) };
    return { ok: true, json: async () => ({}) };
  });
  vi.stubGlobal("fetch", fetchMock);
}

describe("login end-to-end", () => {
  it("swaps the login button for the user menu after a successful login", async () => {
    backend();
    const user = userEvent.setup();
    render(
      <SessionProvider>
        <LoginDialogProvider>
          <Header />
        </LoginDialogProvider>
      </SessionProvider>,
    );

    const loginBtn = await screen.findByRole("button", { name: strings.login });
    await user.click(loginBtn);
    await user.type(await screen.findByLabelText(strings.phoneNumber), "+989123456789");
    await user.click(screen.getByRole("button", { name: strings.sendCode }));
    await user.type(await screen.findByLabelText(strings.enterCode), "123456");
    await user.click(screen.getByRole("button", { name: strings.loginButton }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "+989123456789" })).toBeInTheDocument(),
    );
    expect(screen.queryByRole("button", { name: strings.login })).not.toBeInTheDocument();
  });
});
