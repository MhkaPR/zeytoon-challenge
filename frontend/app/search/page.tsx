"use client";

import { use } from "react";

import { Body, Card, DisplayHero, MonoLabel } from "@/src/components/ui";
import { Header } from "@/src/features/site/Header";
import { strings } from "@/src/lib/i18n/strings";

/**
 * Search page: the search box sticks to the top and matching plans and companies render
 * below it (PAGES.yaml search-box desc). Matching is owned by the search feature, so this
 * shows the query and the pending state.
 */
export default function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const raw = use(searchParams).q;
  const query = Array.isArray(raw) ? (raw[0] ?? "") : (raw ?? "");

  return (
    <>
      <Header />
      <main className="mx-auto flex w-full max-w-[960px] flex-1 flex-col gap-[16px] px-[32px] py-[80px]">
        <DisplayHero className="text-[40px]">{strings.searchTitle}</DisplayHero>
        {query && <MonoLabel>{query}</MonoLabel>}
        <Card variant="plain">
          <Body tone="muted">{strings.resultsPending}</Body>
        </Card>
      </main>
    </>
  );
}
