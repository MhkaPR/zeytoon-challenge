"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { AuthApiError } from "@/src/lib/api/auth";
import { opsStrings } from "@/src/lib/i18n/strings";
import { getAccessToken } from "@/src/lib/session";

/** Map an API failure to a Persian message while keeping the contract code visible. */
export function opsErrorMessage(error: unknown): string {
  if (error instanceof AuthApiError) {
    switch (error.code) {
      case "recipe_incomplete":
        return opsStrings.recipeIncomplete;
      case "trace_required":
        return opsStrings.traceMissing;
      case "labeling_disabled":
        return opsStrings.labelingDisabled;
      case "llm_ceiling_exceeded":
        return opsStrings.ceilingExceeded;
      case "admin_required":
      case "not_authenticated":
        return opsStrings.adminOnly;
      case "domtrack_unreachable":
        return opsStrings.domtrackUnreachable;
      case "capture_failed":
        return opsStrings.captureAborted;
      default:
        return `${opsStrings.genericError} (${error.code})`;
    }
  }
  return opsStrings.genericError;
}

/**
 * Load one console resource with the in-memory access token. ``key`` changes (for example a
 * route id) re-run the loader, and ``reload`` refreshes after a mutation.
 */
export function useOpsData<T>(
  loader: (token: string | null) => Promise<T>,
  key: string = "",
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const activeKey = useRef(key);

  const reload = useCallback(() => {
    setError(null);
    setVersion((value) => value + 1);
  }, []);

  useEffect(() => {
    let active = true;
    if (activeKey.current !== key) {
      activeKey.current = key;
      setData(null);
      setLoading(true);
    }
    loader(getAccessToken())
      .then((result) => {
        if (active) setData(result);
      })
      .catch((failure) => {
        if (active) setError(opsErrorMessage(failure));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
    // The loader is a stable module-level function or a closure over ``key``.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, version]);

  return { data, loading, error, reload };
}
