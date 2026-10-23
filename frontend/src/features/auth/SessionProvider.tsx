"use client";

import { createContext, use, useCallback, useEffect, useMemo, useState } from "react";

import { logout as logoutRequest, type SessionIdentity } from "@/src/lib/api/auth";
import { isGuest, loadIdentity, setAccessToken } from "@/src/lib/session";

interface SessionContextValue {
  /** ``null`` while the identity is still loading. */
  identity: SessionIdentity | null;
  isAuthenticated: boolean;
  /** Re-read the session from the backend (after login, or on demand). */
  refresh: () => Promise<void>;
  /** Revoke the session and drop to the guest state. */
  signOut: () => Promise<void>;
}

const SessionContext = createContext<SessionContextValue | null>(null);

/**
 * App-wide session state. The header, guest gates, and the company panel all read the same
 * identity so a successful login immediately swaps the header's login button for the user
 * menu, and a logout reverses it — without a full page reload (spec FR-010).
 */
export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [identity, setIdentity] = useState<SessionIdentity | null>(null);

  const refresh = useCallback(async () => {
    setIdentity(await loadIdentity());
  }, []);

  const signOut = useCallback(async () => {
    try {
      await logoutRequest();
    } finally {
      setAccessToken(null);
      setIdentity({ authenticated: false, role: "guest" });
    }
  }, []);

  useEffect(() => {
    // Resolve the identity asynchronously so the setState happens in a promise callback
    // rather than synchronously inside the effect body.
    let active = true;
    loadIdentity().then((next) => {
      if (active) setIdentity(next);
    });
    return () => {
      active = false;
    };
  }, []);

  const value = useMemo<SessionContextValue>(
    () => ({
      identity,
      isAuthenticated: identity !== null && !isGuest(identity),
      refresh,
      signOut,
    }),
    [identity, refresh, signOut],
  );

  return <SessionContext value={value}>{children}</SessionContext>;
}

const FALLBACK: SessionContextValue = {
  identity: null,
  isAuthenticated: false,
  refresh: async () => {},
  signOut: async () => {},
};

/** The raw session context, or ``null`` when rendered outside the provider. */
export function useOptionalSession(): SessionContextValue | null {
  return use(SessionContext);
}

/** Read the app-wide session from any client component inside the provider. */
export function useSession(): SessionContextValue {
  return use(SessionContext) ?? FALLBACK;
}
