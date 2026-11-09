"use client";

import { createContext, use, type ReactNode } from "react";

import { DEFAULT_SITE_CONFIG, type SiteConfig } from "@/src/lib/config/siteConfig";

const SiteConfigContext = createContext<SiteConfig>(DEFAULT_SITE_CONFIG);

/** Shares the server-fetched runtime configuration with client components. */
export function SiteConfigProvider({
  children,
  initialConfig = DEFAULT_SITE_CONFIG,
}: {
  children: ReactNode;
  initialConfig?: SiteConfig;
}) {
  return <SiteConfigContext value={initialConfig}>{children}</SiteConfigContext>;
}

/** Read the shared runtime configuration from any client component. */
export function useSiteConfig(): SiteConfig {
  return use(SiteConfigContext);
}
