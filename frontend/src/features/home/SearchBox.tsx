"use client";

import { Button, Label, SearchField } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { strings } from "@/src/lib/i18n/strings";

/**
 * Search entry point. Submitting navigates to the search page with the query, where the
 * matching plans and companies are rendered below the (sticky) search field.
 */
export function SearchBox() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  function submit() {
    const trimmed = query.trim();
    router.push(trimmed ? `/search?q=${encodeURIComponent(trimmed)}` : "/search");
  }

  return (
    <form
      role="search"
      className="flex w-full flex-col items-stretch gap-[8px] sm:flex-row"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <div className="flex-1">
        <SearchField
          aria-label={strings.searchTitle}
          name="q"
          value={query}
          onChange={setQuery}
        >
          <Label className="sr-only">{strings.searchTitle}</Label>
          <SearchField.Group>
            <SearchField.SearchIcon />
            <SearchField.Input placeholder={strings.searchPlaceholder} />
            <SearchField.ClearButton />
          </SearchField.Group>
        </SearchField>
      </div>
    </form>
  );
}
