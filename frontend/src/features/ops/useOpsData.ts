"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useTranslations } from "next-intl";

import { AuthApiError } from "@/src/lib/api/auth";
import { getAccessToken } from "@/src/lib/session";

type Translator = (key: string) => string;

/** Map an API failure to a Persian message while keeping the contract code visible. */
export function opsErrorMessage(error: unknown, ot: Translator): string {
  if (error instanceof AuthApiError) {
    switch (error.code) {
      case "recipe_incomplete":
        return ot("recipeIncomplete");
      case "trace_required":
        return ot("traceMissing");
      case "labeling_disabled":
        return ot("labelingDisabled");
      case "llm_ceiling_exceeded":
        return ot("ceilingExceeded");
      case "admin_required":
      case "not_authenticated":
        return ot("adminOnly");
      case "domtrack_unreachable":
        return ot("domtrackUnreachable");
      case "capture_failed":
        return ot("captureAborted");
      default:
        return `${ot("genericError")} (${error.code})`;
    }
  }
  return ot("genericError");
}

/**
 * Load one console resource with the in-memory access token. ``key`` changes (for example a
 * route id) re-run the loader, and ``reload`` refreshes after a mutation.
 */
export function useOpsData<T>(
  loader: (token: string | null) => Promise<T>,
  key: string = "",
) {
  const ot = useTranslations();
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
        if (active) setError(opsErrorMessage(failure, ot));
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
