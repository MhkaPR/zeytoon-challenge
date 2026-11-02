"use client";

import { Avatar, Chip, ListBox, Typography } from "@heroui/react";

import { strings } from "@/src/lib/i18n/strings";

import type { SearchResult } from "./data";

/**
 * Suggestions shown below the search box while typing: each row is a HeroUI ``ListBox`` item
 * with a company image (or initial), a title, and supporting info. Which kind a row is
 * (company vs plan) is surfaced as text so it does not rely on color.
 */
export function ResultsList({ results }: { results: SearchResult[] }) {
  if (results.length === 0) {
    return (
      <Typography className="px-[16px] py-[24px] text-center" color="muted">
        {strings.noResults}
      </Typography>
    );
  }

  return (
    <ListBox aria-label={strings.resultsTitle} className="p-[8px]" selectionMode="none">
      {results.map((result) => (
        <ListBox.Item id={result.id} key={result.id} textValue={result.title}>
          <Avatar size="sm">
            {result.image ? (
              <Avatar.Image alt="" src={result.image} />
            ) : (
              <Avatar.Fallback>
                {result.kind === "company" ? strings.companyType.slice(0, 1) : strings.planType.slice(0, 1)}
              </Avatar.Fallback>
            )}
          </Avatar>
          <div className="flex flex-col">
            <Typography className="font-medium">{result.title}</Typography>
            <Typography color="muted" type="body-sm">
              {result.subtitle}
            </Typography>
          </div>
          <Chip className="ms-auto" color="accent" size="sm" variant="soft">
            {result.kind === "company" ? strings.companyType : strings.planType}
          </Chip>
        </ListBox.Item>
      ))}
    </ListBox>
  );
}
