"use client";

import { useEffect, useState } from "react";

/**
 * Countdown to the one-time code expiry (spec FR-014). Returns the remaining seconds and a
 * formatted mm:ss string; it stops at zero.
 */
export function useCountdown(seconds: number | null): {
  remaining: number;
  label: string;
  expired: boolean;
} {
  const [remaining, setRemaining] = useState(seconds ?? 0);
  const [tracked, setTracked] = useState(seconds);

  // Reset the countdown when the incoming duration changes. Adjusting state during render is
  // the React-recommended alternative to a state-setting effect for derived-from-prop resets.
  if (seconds !== tracked) {
    setTracked(seconds);
    setRemaining(seconds ?? 0);
  }

  useEffect(() => {
    if (seconds === null) return;
    const timer = setInterval(() => {
      setRemaining((current) => (current <= 1 ? 0 : current - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [seconds]);

  const minutes = Math.floor(remaining / 60);
  const secs = remaining % 60;
  const label = `${minutes}:${String(secs).padStart(2, "0")}`;
  return { remaining, label, expired: remaining <= 0 };
}
