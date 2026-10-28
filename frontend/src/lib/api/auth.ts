/**
 * Typed client for the authentication API (see specs/001-sms-otp-login/contracts/auth-api.md).
 *
 * The access token is kept in memory (never in localStorage) to reduce XSS exposure; the
 * refresh token lives in an httpOnly cookie set by the backend.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type Role = "guest" | "regular" | "ops" | "admin";

export interface SessionIdentity {
  authenticated: boolean;
  role?: Role;
  user?: { phone: string; role: Role };
}

export interface VerifyResult {
  access_token: string;
  token_type: string;
  expires_in: number;
  redirect_to: string;
  user: { phone: string; role: Role };
}

export interface ApiErrorBody {
  error: { code: string; message: string; fields?: Record<string, unknown> };
}

export class AuthApiError extends Error {
  code: string;
  fields: Record<string, unknown>;

  constructor(code: string, message: string, fields: Record<string, unknown> = {}) {
    super(message);
    this.name = "AuthApiError";
    this.code = code;
    this.fields = fields;
  }
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[2]) : null;
}

async function request<T>(path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const csrf = readCookie("csrftoken");
  if (csrf) headers["X-CSRFToken"] = csrf;

  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers,
    credentials: "include",
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = (data as ApiErrorBody).error;
    throw new AuthApiError(
      error?.code ?? "unknown_error",
      error?.message ?? "Something went wrong.",
      error?.fields ?? {},
    );
  }
  return data as T;
}

export function requestOtp(phoneNumber: string) {
  return request<{ status: string; expires_in_seconds: number }>(
    "/api/v1/auth/otp/request",
    { phone_number: phoneNumber },
  );
}

export function verifyOtp(phoneNumber: string, code: string, returnUrl?: string) {
  return request<VerifyResult>("/api/v1/auth/otp/verify", {
    phone_number: phoneNumber,
    code,
    return_url: returnUrl,
  });
}

/**
 * Read the current identity. The backend resolves the user from the ``Authorization: Bearer``
 * header (contracts/auth-api.md §GET /session), so the in-memory access token MUST be sent;
 * without it the request is always treated as a guest.
 */
export async function getSession(accessToken?: string | null): Promise<SessionIdentity> {
  const headers: Record<string, string> = {};
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const response = await fetch(`${API_BASE}/api/v1/auth/session`, {
    headers,
    credentials: "include",
  });
  return (await response.json()) as SessionIdentity;
}

/** Exchange the httpOnly refresh cookie for a fresh access token (rotating refresh). */
export function refreshAccessToken() {
  return request<{ access_token: string; token_type: string; expires_in: number }>(
    "/api/v1/auth/token/refresh",
  );
}

export function logout() {
  return request<{ status: string }>("/api/v1/auth/logout");
}
