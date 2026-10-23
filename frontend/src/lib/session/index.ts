/**
 * Client-side session state.
 *
 * The access token is held in memory only; the refresh token is an httpOnly cookie managed
 * by the backend. This module is the single place the app reads the guest/authenticated
 * signal from (spec FR-010).
 */

import {
  getSession,
  refreshAccessToken,
  type SessionIdentity,
} from "@/src/lib/api/auth";

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export async function loadIdentity(): Promise<SessionIdentity> {
  // The access token lives in memory with the httpOnly refresh cookie as the durable
  // credential. After a page reload the in-memory token is gone, so recover one from the
  // refresh cookie before asking for the identity (spec FR-010).
  if (!accessToken) {
    try {
      const refreshed = await refreshAccessToken();
      accessToken = refreshed.access_token;
    } catch {
      return { authenticated: false, role: "guest" };
    }
  }
  return getSession(accessToken);
}

export function isGuest(identity: SessionIdentity): boolean {
  return identity.authenticated !== true;
}
