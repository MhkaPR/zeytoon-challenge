import { NextResponse, type NextRequest } from "next/server";

const VISITOR_COOKIE = "visitor_id";
const MAX_AGE = 60 * 60 * 24 * 180;

/** Issues an opaque device id and exposes it to the current server render. */
export function middleware(request: NextRequest) {
  const existing = request.cookies.get(VISITOR_COOKIE)?.value;
  const visitorId = existing ?? crypto.randomUUID();

  const headers = new Headers(request.headers);
  headers.set("x-visitor-id", visitorId);

  const response = NextResponse.next({ request: { headers } });
  if (!existing) {
    response.cookies.set({
      name: VISITOR_COOKIE,
      value: visitorId,
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: MAX_AGE,
    });
  }
  return response;
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
