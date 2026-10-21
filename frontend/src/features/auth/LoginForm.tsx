"use client";

import { useState } from "react";

import { AuthApiError, requestOtp, verifyOtp } from "@/src/lib/api/auth";
import { setAccessToken } from "@/src/lib/session";

import { consumeReturnUrl } from "./returnUrl";
import { useCountdown } from "./useCountdown";

type Step = "phone" | "code";

export interface LoginFormProps {
  /** Called with the validated redirect target after a successful login. */
  onSuccess?: (redirectTo: string) => void;
}

/**
 * Two-step phone + SMS OTP login form. Handles the expiry countdown and the required
 * "The code is incorrect" message (spec FR-015).
 */
export function LoginForm({ onSuccess }: LoginFormProps) {
  const [step, setStep] = useState<Step>("phone");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [ttl, setTtl] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const { label, expired } = useCountdown(ttl);

  async function handleRequest(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result = await requestOtp(phone);
      setTtl(result.expires_in_seconds);
      setStep("code");
    } catch (err) {
      setError(err instanceof AuthApiError ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  async function handleVerify(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result = await verifyOtp(phone, code, consumeReturnUrl());
      setAccessToken(result.access_token);
      onSuccess?.(result.redirect_to);
    } catch (err) {
      // Expired and wrong codes produce the same message by design.
      setError(err instanceof AuthApiError ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  if (step === "phone") {
    return (
      <form onSubmit={handleRequest} aria-label="login-phone">
        <label htmlFor="phone">Phone number</label>
        <input
          id="phone"
          name="phone"
          inputMode="tel"
          value={phone}
          onChange={(event) => setPhone(event.target.value)}
          required
        />
        {error && <p role="alert">{error}</p>}
        <button type="submit" disabled={busy}>
          Send code
        </button>
      </form>
    );
  }

  return (
    <form onSubmit={handleVerify} aria-label="login-code">
      <label htmlFor="code">Enter the code sent by SMS</label>
      <input
        id="code"
        name="code"
        inputMode="numeric"
        value={code}
        onChange={(event) => setCode(event.target.value)}
        required
      />
      <p aria-label="countdown">
        {expired ? "Request a new code" : `Time remaining ${label}`}
      </p>
      {error && <p role="alert">{error}</p>}
      <button type="submit" disabled={busy}>
        Log in
      </button>
    </form>
  );
}
