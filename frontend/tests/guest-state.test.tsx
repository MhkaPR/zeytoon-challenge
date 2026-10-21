import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GuestGate } from "@/src/features/auth/GuestGate";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("GuestGate", () => {
  it("prompts a guest to log in", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ authenticated: false, role: "guest" }),
      }),
    );
    render(
      <GuestGate>
        <p>protected content</p>
      </GuestGate>,
    );

    await waitFor(() =>
      expect(screen.getByText(/please log in to continue/i)).toBeInTheDocument(),
    );
    expect(screen.queryByText("protected content")).not.toBeInTheDocument();
  });

  it("renders protected content for an authenticated user", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          authenticated: true,
          user: { phone_masked: "+98***6789", role: "regular" },
        }),
      }),
    );
    render(
      <GuestGate>
        <p>protected content</p>
      </GuestGate>,
    );

    await waitFor(() =>
      expect(screen.getByText("protected content")).toBeInTheDocument(),
    );
  });
});
