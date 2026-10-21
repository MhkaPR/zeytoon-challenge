/**
 * Client-side session state.
 *
 * The access token is held in memory only; the refresh token is an httpOnly cookie managed
 * by the backend. This module is the single place the app reads the guest/authenticated
 * signal from (spec FR-010).
 */

import { getSession, type SessionIdentity } from "@/src/lib/api/auth";

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export async function loadIdentity(): Promise<SessionIdentity> {
  return getSession();
}

export function isGuest(identity: SessionIdentity): boolean {
  return identity.authenticated !== true;
}
