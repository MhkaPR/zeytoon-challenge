"use client";

import { Typography } from "@heroui/react";
import { useEffect, useState } from "react";

import type { SessionIdentity } from "@/src/lib/api/auth";
import { strings } from "@/src/lib/i18n/strings";
import { isGuest, loadIdentity } from "@/src/lib/session";

import { LoginForm } from "./LoginForm";

export interface GuestGateProps {
  children: React.ReactNode;
}

/**
 * Renders protected content for authenticated users and prompts guests to log in, returning
 * them to the originating page afterwards (spec FR-010, US2).
 */
export function GuestGate({ children }: GuestGateProps) {
  const [identity, setIdentity] = useState<SessionIdentity | null>(null);

  useEffect(() => {
    loadIdentity().then(setIdentity);
  }, []);

  if (identity === null) return null;
  if (isGuest(identity)) {
    return (
      <div className="flex flex-col gap-[16px]">
        <Typography>{strings.pleaseLogin}</Typography>
        <LoginForm onSuccess={(redirectTo) => window.location.assign(redirectTo || "/")} />
      </div>
    );
  }
  return <>{children}</>;
}
