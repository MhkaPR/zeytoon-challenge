/**
 * Return-URL handling.
 *
 * The captured target is stored so the user can be returned to the page they were on before
 * login. The backend re-validates it against its allowlist; an invalid target falls back to
 * the default page (spec FR-011).
 */

export const RETURN_URL_STORAGE_KEY = "auth:returnUrl";

export function captureReturnUrl(): string | undefined {
  if (typeof window === "undefined") return undefined;
  const target = window.location.pathname + window.location.search;
  if (target && target !== "/login") {
    window.sessionStorage.setItem(RETURN_URL_STORAGE_KEY, target);
  }
  return target;
}

export function consumeReturnUrl(): string | undefined {
  if (typeof window === "undefined") return undefined;
  const target = window.sessionStorage.getItem(RETURN_URL_STORAGE_KEY) ?? undefined;
  if (target) window.sessionStorage.removeItem(RETURN_URL_STORAGE_KEY);
  return target;
}
