"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { SearchInput } from "@/src/features/ui/SearchInput";

/** Company-directory search; submits the query to the server-rendered page. */
export function CompanySearchBox({ initialQuery }: { initialQuery: string }) {
  const ot = useTranslations();
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);

  function submit(value: string) {
    const trimmed = value.trim();
    router.push(trimmed ? `/companies?q=${encodeURIComponent(trimmed)}` : "/companies");
  }

  return (
    <SearchInput
      ariaLabel={ot("searchCompany")}
      className="flex w-full max-w-[520px] items-center gap-[8px]"
      name="q"
      placeholder={ot("companyName")}
      value={query}
      variant="primary"
      onChange={setQuery}
      onSubmit={submit}
    />
  );
}
