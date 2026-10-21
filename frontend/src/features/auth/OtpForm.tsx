"use client";

import { useCountdown } from "./useCountdown";

export interface OtpFormProps {
  expiresInSeconds: number | null;
}

/**
 * Presentational wrapper around the code-entry step, exposing the expiry countdown so the
 * remaining time is visible (spec FR-014).
 */
export function OtpForm({ expiresInSeconds }: OtpFormProps) {
  const { label, expired } = useCountdown(expiresInSeconds);
  return (
    <p aria-label="otp-countdown">
      {expired ? "Request a new code" : `Time remaining ${label}`}
    </p>
  );
}
