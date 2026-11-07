import { describe, expect, it, vi } from "vitest";

import { sendSignal } from "@/src/lib/api/signals";

describe("signal client", () => {
  it("posts the expected payload", () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);
    sendSignal("details_view", [42]);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/recommendations/signals"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ kind: "details_view", plan_ids: [42] }),
      }),
    );
    vi.unstubAllGlobals();
  });

  it("does nothing without plan ids", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    sendSignal("details_view", []);
    expect(fetchMock).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});
