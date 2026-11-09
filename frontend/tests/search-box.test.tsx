import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SearchBox } from "@/src/features/home/SearchBox";
import { strings } from "./messages";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

beforeEach(() => {
  push.mockReset();
});

describe("SearchBox", () => {
  it("initializes from the current query and submits a new search", async () => {
    const user = userEvent.setup();
    render(<SearchBox initialQuery="python" />);

    const input = screen.getByRole("searchbox");
    expect(input).toHaveValue("python");

    await user.clear(input);
    await user.type(input, "django");
    await user.click(screen.getByRole("button", { name: strings.searchSubmit }));

    expect(push).toHaveBeenCalledWith("/search?q=django");
  });
});
