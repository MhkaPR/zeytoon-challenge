"use client";

import { Card, Chip, Typography } from "@heroui/react";
import { use } from "react";

import { SearchBox } from "@/src/features/home/SearchBox";
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
    <main className="mx-auto flex w-full max-w-[960px] flex-1 flex-col gap-[24px] px-[32px] py-[64px]">
      <Typography className="text-[32px] font-semibold" type="h1">
        {strings.searchTitle}
      </Typography>
      <SearchBox />
      {query && <Chip variant="soft">{query}</Chip>}
      <Card variant="secondary">
        <Card.Header>
          <Card.Title>{strings.resultsEmptyTitle}</Card.Title>
          <Card.Description>{strings.resultsPending}</Card.Description>
        </Card.Header>
      </Card>
    </main>
  );
}
