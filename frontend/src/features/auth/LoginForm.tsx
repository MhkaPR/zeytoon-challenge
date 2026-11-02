"use client";

import { useTranslations } from "next-intl";
import { Button, Input, Label, TextField, Typography } from "@heroui/react";
import { useState } from "react";

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
  const t = useTranslations("common");
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
      setError(err instanceof AuthApiError ? localizeError(err) : t("genericError"));
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
      setError(err instanceof AuthApiError ? localizeError(err) : t("genericError"));
    } finally {
      setBusy(false);
    }
  }

  if (step === "phone") {
    return (
      <form onSubmit={handleRequest} aria-label="login-phone" className="flex flex-col gap-[16px]">
        <TextField
          isRequired
          name="phone"
          value={phone}
          onChange={setPhone}
        >
          <Label>{t("phoneNumber")}</Label>
          <Input inputMode="tel" placeholder={t("phonePlaceholder")} />
        </TextField>
        {error && (
          <Typography className="text-[14px] text-danger" role="alert">
            {error}
          </Typography>
        )}
        <Button isDisabled={busy} type="submit">
          {t("sendCode")}
        </Button>
      </form>
    );
  }

  return (
    <form onSubmit={handleVerify} aria-label="login-code" className="flex flex-col gap-[16px]">
      <TextField isRequired name="code" value={code} onChange={setCode}>
        <Label>{t("enterCode")}</Label>
        <Input autoComplete="one-time-code" inputMode="numeric" />
      </TextField>
      <Typography aria-label="countdown" className="text-[12px] text-muted">
        {expired ? t("requestNewCode") : `${t("timeRemaining")} ${label}`}
      </Typography>
      {error && (
        <Typography className="text-[14px] text-danger" role="alert">
          {error}
        </Typography>
      )}
      <Button isDisabled={busy} type="submit">
        {t("loginButton")}
      </Button>
    </form>
  );
}
