import { Suspense } from "react";

import { Skeleton } from "@heroui/react";

import OpsSitePageClient from "./OpsSitePageClient";

export default function OpsSitePage({ params }: { params: Promise<{ siteId: string }> }) {
  return (
    <Suspense fallback={<Skeleton className="h-[220px] rounded-[var(--radius)]" />}>
      <OpsSitePageClient params={params} />
    </Suspense>
  );
}
