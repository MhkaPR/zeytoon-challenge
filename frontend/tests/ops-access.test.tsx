import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { SessionIdentity } from "@/src/lib/api/auth";
import { identityRole } from "@/src/lib/session";

const { replace, session } = vi.hoisted(() => ({
  replace: vi.fn(),
  session: {
    current: { authenticated: false, role: "guest" } as SessionIdentity,
  },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  usePathname: () => "/ops",
}));

vi.mock("@/src/features/auth/SessionProvider", () => ({
  useSession: () => ({ identity: session.current }),
}));

vi.mock("@/src/features/auth/LoginButton", () => ({
  LoginButton: () => <button type="button">login</button>,
}));

import OpsLayout from "@/app/ops/layout";
import { opsStrings } from "@/src/lib/i18n/strings";

beforeEach(() => {
  replace.mockReset();
  session.current = { authenticated: false, role: "guest" };
});

describe("ops access role", () => {
  it("reads the role from the user payload when the top level omits it", () => {
    const identity: SessionIdentity = {
      authenticated: true,
      user: { phone: "09123456789", role: "admin" },
    };

    expect(identityRole(identity)).toBe("admin");
  });

  it("treats guests as guests", () => {
    expect(identityRole({ authenticated: false, role: "guest" })).toBe("guest");
    expect(identityRole(null)).toBe("guest");
  });

  it("shows the login prompt to guests instead of redirecting", () => {
    render(
      <OpsLayout>
        <div>console data</div>
      </OpsLayout>,
    );

    expect(screen.getByText(opsStrings.adminOnly)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "login" })).toBeInTheDocument();
    expect(screen.queryByText("console data")).not.toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });

  it("renders the console for admins whose role is only inside the user payload", () => {
    session.current = {
      authenticated: true,
      user: { phone: "09123456789", role: "admin" },
    };

    render(
      <OpsLayout>
        <div>console data</div>
      </OpsLayout>,
    );

    expect(screen.getByText("console data")).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });
});
