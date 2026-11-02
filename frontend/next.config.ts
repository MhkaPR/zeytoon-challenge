import type { NextConfig } from "next";

// Where the API lives. When deployed, set ``NEXT_PUBLIC_API_BASE_URL`` to the absolute
// backend origin. When it is unset (the local development default) the frontend talks to the
// API on its own origin and Next proxies those requests below.
const API_ORIGIN = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  // Serve the API under the frontend origin when no external base URL is configured, so the
  // backend's httpOnly refresh cookie is first-party. A cross-origin cookie (localhost:3000 ->
  // localhost:8000) with SameSite=Strict is fragile: cookies can be dropped, and the session
  // then dies on reload. Same-origin removes that whole class of failure.
  async rewrites() {
    if (process.env.NEXT_PUBLIC_API_BASE_URL) return [];
    return [{ source: "/api/:path*", destination: `${API_ORIGIN}/api/:path*` }];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
