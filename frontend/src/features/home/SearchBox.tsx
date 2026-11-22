"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { SearchInput } from "@/src/features/ui/SearchInput";

/**
 * Search entry point. Submitting navigates to the search page with the query, where the
 * matching plans and companies are rendered below the (sticky) search field.
 */
export function SearchBox({ initialQuery = "" }: { initialQuery?: string }) {
  const ot = useTranslations();
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);

  useEffect(() => {
    setQuery(initialQuery);
  }, [initialQuery]);

  function submit(value: string) {
    const trimmed = value.trim();
    router.push(trimmed ? `/search?q=${encodeURIComponent(trimmed)}` : "/search");
  }

  return (
    <SearchInput
      ariaLabel={ot("searchTitle")}
      name="q"
      placeholder={ot("searchPlaceholder")}
      value={query}
      onChange={setQuery}
      onSubmit={submit}
    />
  );
}
