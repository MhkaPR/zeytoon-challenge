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
  type Role,
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

/**
 * The effective role of an identity. The backend puts it both at the top level and inside
 * ``user``; older payloads only carry ``user.role``, so fall back to that.
 */
export function identityRole(identity: SessionIdentity | null): Role {
  if (!identity?.authenticated) return "guest";
  return identity.user?.role ?? identity.role ?? "guest";
}

/** ``ops`` and ``admin`` may use the operator console; admins are a superset. */
export function isOperatorRole(role: Role): boolean {
  return role === "admin" || role === "ops";
}
