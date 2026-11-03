import { SearchPageClient } from "./SearchPageClient";

// The search query is runtime data; allow the segment to wait for it during prerendering.
export const instant = false;

/** Search route shell: resolves the query, then hands off to the client-rendered SPA view. */
export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const raw = (await searchParams).q;
  const query = Array.isArray(raw) ? (raw[0] ?? "") : (raw ?? "");
  return <SearchPageClient query={query} />;
}
