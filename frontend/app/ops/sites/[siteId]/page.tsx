import { Suspense } from "react";

import { Skeleton } from "@/src/features/ui/heroUi";

import OpsSitePageClient from "./OpsSitePageClient";

// This page fetches operator-specific data in the browser and polls for updates. Its initial
// route shell cannot contain that data, so allow the segment to wait for its rendered UI.
export const instant = false;

export default function OpsSitePage({ params }: { params: Promise<{ siteId: string }> }) {
  return (
    <Suspense fallback={<Skeleton className="h-[220px] rounded-[var(--radius)]" />}>
      <OpsSitePageClient params={params} />
    </Suspense>
  );
}
