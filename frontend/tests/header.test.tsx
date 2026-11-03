import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/",
}));

import { LoginDialogProvider } from "@/src/features/auth/LoginDialog";
import { SessionProvider } from "@/src/features/auth/SessionProvider";
import { Header } from "@/src/features/site/Header";
import { setAccessToken } from "@/src/lib/session";
import { strings } from "./messages";

afterEach(() => {
  vi.restoreAllMocks();
  setAccessToken(null);
});

describe("header", () => {
  it("shows a recognizable national-format phone and the menu button", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      json: async () => ({ authenticated: true, user: { phone: "09123456789", role: "regular" } }),
    })));
    render(
      <SessionProvider>
        <LoginDialogProvider>
          <Header />
        </LoginDialogProvider>
      </SessionProvider>,
    );
    // The phone number is visible without opening anything.
    await waitFor(() => expect(screen.getByText("0912***6789")).toBeInTheDocument());
    // The mobile menu button is present.
    expect(screen.getByRole("button", { name: strings.menuOpen })).toBeInTheDocument();
  });
});
