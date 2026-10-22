"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button, Input } from "@/src/components/ui";
import { strings } from "@/src/lib/i18n/strings";

/**
 * Search entry point. Submitting navigates to the search page with the query, where the
 * matching plans and companies are rendered below the (sticky) search field.
 */
export function SearchBox() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  return (
    <form
      role="search"
      className="flex w-full flex-col items-stretch gap-[8px] sm:flex-row"
      onSubmit={(event) => {
        event.preventDefault();
        const trimmed = query.trim();
        router.push(trimmed ? `/search?q=${encodeURIComponent(trimmed)}` : "/search");
      }}
    >
      <div className="flex-1">
        <Input
          type="search"
          name="q"
          aria-label={strings.searchTitle}
          placeholder={strings.searchPlaceholder}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>
      <Button type="submit" variant="primary" className="sm:self-end">
        {strings.searchSubmit}
      </Button>
    </form>
  );
}
