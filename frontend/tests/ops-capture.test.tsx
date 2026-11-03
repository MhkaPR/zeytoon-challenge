import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CapturePanel } from "@/src/features/ops/capture/CapturePanel";
import type { CaptureSession } from "@/src/lib/api/ops";
import { opsStrings } from "./messages";

afterEach(() => {
  vi.restoreAllMocks();
});

const capture: CaptureSession = {
  id: 21,
  link_id: 11,
  mode: "fixed",
  state: "recorded",
  local_path: "/tmp/trace.json",
  duration_ms: 30000,
  error: "",
  trace_id: null,
};

function props(overrides: Partial<React.ComponentProps<typeof CapturePanel>> = {}) {
  return {
    stage: "capture",
    capture: null,
    traceStored: false,
    onStart: vi.fn(),
    onUpload: vi.fn(),
    onLoadLocal: vi.fn(),
    onFail: vi.fn(),
    onContinue: vi.fn(),
    onRecheck: vi.fn(),
    ...overrides,
  };
}

describe("capture panel", () => {
  it("offers interactive and fixed-duration modes and passes the duration", async () => {
    const onStart = vi.fn();
    const user = userEvent.setup();
    render(<CapturePanel {...props({ onStart })} />);

    await user.click(screen.getByText(opsStrings.modeFixed));
    const duration = screen.getByLabelText(opsStrings.durationMs);
    await user.clear(duration);
    await user.type(duration, "45000");
    await user.click(screen.getByText(opsStrings.startCapture));

    expect(onStart).toHaveBeenCalledWith("fixed_duration", 45000);
  });

  it("explains when domtrack is unreachable", () => {
    render(<CapturePanel {...props({ errorCode: "domtrack_unreachable" })} />);
    expect(screen.getByText(opsStrings.domtrackUnreachable)).toBeInTheDocument();
  });

  it("offers a manual upload fallback after a capture", async () => {
    const onUpload = vi.fn();
    const user = userEvent.setup();
    const file = new File(["trace"], "trace.json", { type: "application/json" });
    render(<CapturePanel {...props({ capture, onUpload })} />);

    expect(screen.getByText(opsStrings.manualUploadTitle)).toBeInTheDocument();
    await user.upload(screen.getByLabelText(opsStrings.uploadTrace), file);
    await user.click(
      screen.getByRole("button", { name: opsStrings.uploadTrace }),
    );
    expect(onUpload).toHaveBeenCalledWith(file);
  });

  it("blocks advancing until a trace is stored", () => {
    render(<CapturePanel {...props()} />);
    expect(screen.getByText(opsStrings.traceMissing)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: opsStrings.advanceBlocked }),
    ).toBeDisabled();
  });

  it("disables starting a second capture while one is in progress", () => {
    render(<CapturePanel {...props({ activeCapture: capture })} />);

    expect(screen.getByText(opsStrings.captureInProgress)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: new RegExp(opsStrings.startCapture) }),
    ).toBeDisabled();
  });

  it("loads the trace from domtrack's local path", async () => {
    const onLoadLocal = vi.fn();
    const user = userEvent.setup();
    render(<CapturePanel {...props({ capture, onLoadLocal })} />);

    await user.click(
      screen.getByRole("button", { name: new RegExp(opsStrings.loadLocalTrace) }),
    );

    expect(onLoadLocal).toHaveBeenCalled();
  });
});
