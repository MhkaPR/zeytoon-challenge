"use client";

import { useState } from "react";

import { Badge, Body, Button, Input } from "@/src/components/ui";
import { AuthApiError, requestOtp, verifyOtp } from "@/src/lib/api/auth";
import { strings } from "@/src/lib/i18n/strings";
import { setAccessToken } from "@/src/lib/session";

import { consumeReturnUrl } from "./returnUrl";
import { useCountdown } from "./useCountdown";

type Step = "phone" | "code";

export interface LoginFormProps {
  /** Called with the validated redirect target after a successful login. */
  onSuccess?: (redirectTo: string) => void;
}

/**
 * Map a backend error code to a Persian message. The API contract keeps the exact English
 * "The code is incorrect" text; the UI presents the localized equivalent (DESIGN.md §8).
 */
function localizeError(error: AuthApiError): string {
  switch (error.code) {
    case "otp_incorrect":
      return strings.codeIncorrect;
    case "invalid_phone":
      return "شماره موبایل نامعتبر است.";
    case "user_blocked":
      return "برای رفع مسدودی از طریق راههای ارتباطی زیر با ما در تماس باشید.";
    case "locked_out":
    case "too_many_attempts":
    case "rate_limited":
      return "تعداد تلاشها زیاد است. کمی بعد دوباره تلاش کنید.";
    default:
      return strings.genericError;
  }
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
      setError(err instanceof AuthApiError ? localizeError(err) : strings.genericError);
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
      setError(err instanceof AuthApiError ? localizeError(err) : strings.genericError);
    } finally {
      setBusy(false);
    }
  }

  if (step === "phone") {
    return (
      <form onSubmit={handleRequest} aria-label="login-phone" className="flex flex-col gap-[16px]">
        <Input
          id="phone"
          name="phone"
          label={strings.phoneNumber}
          inputMode="tel"
          placeholder={strings.phonePlaceholder}
          value={phone}
          onChange={(event) => setPhone(event.target.value)}
          required
        />
        {error && (
          <Body role="alert" className="text-[14px] text-[var(--ds-blue-900)]">
            {error}
          </Body>
        )}
        <Button type="submit" disabled={busy}>
          {strings.sendCode}
        </Button>
      </form>
    );
  }

  return (
    <form onSubmit={handleVerify} aria-label="login-code" className="flex flex-col gap-[16px]">
      <Input
        id="code"
        name="code"
        label={strings.enterCode}
        inputMode="numeric"
        autoComplete="one-time-code"
        value={code}
        onChange={(event) => setCode(event.target.value)}
        required
      />
      <Badge aria-label="countdown">
        {expired ? strings.requestNewCode : `${strings.timeRemaining} ${label}`}
      </Badge>
      {error && (
        <Body role="alert" className="text-[14px] text-[var(--ds-blue-900)]">
          {error}
        </Body>
      )}
      <Button type="submit" disabled={busy}>
        {strings.loginButton}
      </Button>
    </form>
  );
}
