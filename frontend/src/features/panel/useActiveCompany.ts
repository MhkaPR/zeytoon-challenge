"use client";

import { useCallback, useEffect, useState } from "react";

import {
  getPanelEntry,
  getPanelSwitcher,
  type PanelEntry,
  type SwitcherPayload,
} from "@/src/lib/api/companies";
import { getAccessToken } from "@/src/lib/session";

/** Read the switcher payload and resolve the entry view for the active company. */
export function useActiveCompany(companyId?: number) {
  const [switcher, setSwitcher] = useState<SwitcherPayload | null>(null);
  const [entry, setEntry] = useState<PanelEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setError("unauthorized");
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await getPanelSwitcher(token);
      setSwitcher(data);
      if (companyId) {
        setEntry(await getPanelEntry(token, companyId));
      }
    } catch {
      setError("load_failed");
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    load();
  }, [load]);

  return { switcher, entry, loading, error, reload: load };
}
