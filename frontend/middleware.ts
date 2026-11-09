import { NextResponse, type NextRequest } from "next/server";

const VISITOR_COOKIE = "visitor_id";
const MAX_AGE = 60 * 60 * 24 * 180;

/** Issues an opaque device id and exposes it to the current server render. */
export function middleware(request: NextRequest) {
  const existing = request.cookies.get(VISITOR_COOKIE)?.value;
  const visitorId = existing ?? crypto.randomUUID();
  const forwardedProto = request.headers
    .get("x-forwarded-proto")
    ?.split(",")[0]
    .trim();
  const protocol = forwardedProto ?? request.nextUrl.protocol.replace(":", "");

  const headers = new Headers(request.headers);
  headers.set("x-visitor-id", visitorId);

  const response = NextResponse.next({ request: { headers } });
  if (!existing) {
    response.cookies.set({
      name: VISITOR_COOKIE,
      value: visitorId,
      httpOnly: true,
      sameSite: "lax",
      // Only mark Secure when the request is actually HTTPS. In production behind plain
      // HTTP the browser would reject the cookie, giving every navigation a new id and
      // dropping interest signals before the suggestions endpoint can use them.
      secure: protocol === "https",
      path: "/",
      maxAge: MAX_AGE,
    });
  }
  return response;
}

export const config = {
  // Skip only real static assets, not dynamic segments that contain a dot (for example
  // ``/companies/example.com``). A blanket ``.*\..*`` exclusion also skipped company pages,
  // so they rendered without an ``x-visitor-id`` header and the "recommended for you" order
  // fell back to the cold-start ranking until the client refetched with the visitor cookie.
  matcher: [
    "/((?!api|_next|favicon.ico|.*\\.(?:ico|png|jpe?g|gif|svg|webp|avif|css|js|mjs|map|txt|xml|json|woff2?|ttf|otf)$).*)",
  ],
};
