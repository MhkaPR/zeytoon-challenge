"use client";

import { createContext, use, useEffect, useState, type ReactNode } from "react";

import {
  DEFAULT_SITE_CONFIG,
  getSiteConfig,
  type SiteConfig,
} from "@/src/lib/config/siteConfig";

const SiteConfigContext = createContext<SiteConfig>(DEFAULT_SITE_CONFIG);

/** Loads the backend-owned frontend configuration once for the whole SPA. */
export function SiteConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<SiteConfig>(DEFAULT_SITE_CONFIG);

  useEffect(() => {
    let active = true;
    getSiteConfig().then((next) => {
      if (active) setConfig(next);
    });
    return () => {
      active = false;
    };
  }, []);

  return <SiteConfigContext value={config}>{children}</SiteConfigContext>;
}

/** Read the shared runtime configuration from any client component. */
export function useSiteConfig(): SiteConfig {
  return use(SiteConfigContext);
}
