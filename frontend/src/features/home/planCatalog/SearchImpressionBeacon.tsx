"use client";

import { useEffect, useRef } from "react";

import { sendSignal } from "@/src/lib/api/signals";

/** Records one search-impression signal for the first page of a submitted query. */
export function SearchImpressionBeacon({
  query,
  planIds,
}: {
  query: string;
  planIds: number[];
}) {
  const sent = useRef<string | null>(null);

  useEffect(() => {
    if (!query.trim() || planIds.length === 0) return;
    if (sent.current === query) return;
    sent.current = query;
    sendSignal("search_impression", planIds, query);
  }, [query, planIds]);

  return null;
}
