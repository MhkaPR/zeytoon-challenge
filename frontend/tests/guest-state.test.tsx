import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GuestGate } from "@/src/features/auth/GuestGate";
import { strings } from "./messages";

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
      expect(screen.getByText(strings.pleaseLogin)).toBeInTheDocument(),
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
          user: { phone: "+989046993150", role: "regular" },
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
