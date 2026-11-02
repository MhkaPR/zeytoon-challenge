"use client";

import { useTranslations } from "next-intl";
import { Button, Typography } from "@heroui/react";
import { useEffect, useState } from "react";

import type { SessionIdentity } from "@/src/lib/api/auth";
import { isGuest, loadIdentity } from "@/src/lib/session";

import { useLoginDialog } from "./LoginDialog";
import { useOptionalSession } from "./SessionProvider";

export interface GuestGateProps {
  children: React.ReactNode;
}

/**
 * Renders protected content for authenticated users and prompts guests to log in, returning
 * them to the originating page afterwards (spec FR-010, US2).
 */
export function GuestGate({ children }: GuestGateProps) {
  const t = useTranslations("common");
  const session = useOptionalSession();
  // Fallback identity for isolated renders (e.g. tests) where no provider is present.
  const [localIdentity, setLocalIdentity] = useState<SessionIdentity | null>(null);
  const { open, isOpen } = useLoginDialog();

  useEffect(() => {
    if (session) return;
    loadIdentity().then(setLocalIdentity);
  }, [session]);

  const identity = session ? session.identity : localIdentity;
  const isAuthenticated = session ? session.isAuthenticated : Boolean(identity && !isGuest(identity));

  if (identity === null) return null;
  if (!isAuthenticated) {
    return (
      <div className="flex flex-col gap-[16px]">
        <Typography>{t("pleaseLogin")}</Typography>
        {!isOpen && <Button onPress={open}>{t("login")}</Button>}
      </div>
    );
  }
  return <>{children}</>;
}
