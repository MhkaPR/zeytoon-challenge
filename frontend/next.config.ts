import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

// Pin the workspace root to this app. Without it, a lockfile in a parent directory
// makes Next nest the standalone output under a subfolder, which breaks the Docker
// ``COPY --from=builder /app/.next/standalone ./`` step and ``yarn preview``.
const APP_ROOT = path.dirname(fileURLToPath(import.meta.url));
// Server-side proxy target for ``/api/*``. This is read at BUILD time (rewrites are baked
// into routes-manifest.json), so containers set it via the ``API_PROXY_TARGET`` build arg.
// In Compose that is ``http://backend:8000``; locally it falls back to the dev server.
const API_PROXY_TARGET =
  process.env.API_PROXY_TARGET ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";
dotenv.config({ path: path.resolve(process.cwd(), '../.env') });
const nextConfig: NextConfig = {
  /* config options here */
  output: "standalone",
  turbopack: {
    root: APP_ROOT,
  },
  cacheComponents: true,
  partialPrefetching: true,
  // Always serve the API under the frontend origin so the backend's httpOnly refresh cookie is
  // first-party. A cross-origin cookie (localhost:3000 -> localhost:8000) with SameSite=Strict
  // is fragile: cookies can be dropped, and the session then dies on reload.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_PROXY_TARGET}/api/:path*` }];
  },
  logging: {
    fetches: {
      fullUrl: false,
      hmrRefreshes: true,
    },
    serverFunctions: true,
  },
};

const withNextIntl = createNextIntlPlugin("./src/lib/i18n/request.ts");

export default withNextIntl(nextConfig);
