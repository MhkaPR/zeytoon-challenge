"use client";

import { Label, SearchField } from "@heroui/react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";

/** Company-directory search; submits the query to the server-rendered page. */
export function CompanySearchBox({ initialQuery }: { initialQuery: string }) {
  const ot = useTranslations();
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);

  function submit() {
    const trimmed = query.trim();
    router.push(trimmed ? `/companies?q=${encodeURIComponent(trimmed)}` : "/companies");
  }

  return (
    <form
      className="w-full max-w-[520px]"
      role="search"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <SearchField
        aria-label={ot("searchCompany")}
        name="q"
        value={query}
        variant="secondary"
        onChange={setQuery}
      >
        <Label className="sr-only">{ot("searchCompany")}</Label>
        <SearchField.Group>
          <SearchField.SearchIcon />
          <SearchField.Input placeholder={ot("companyName")} />
          <SearchField.ClearButton />
        </SearchField.Group>
      </SearchField>
    </form>
  );
}
