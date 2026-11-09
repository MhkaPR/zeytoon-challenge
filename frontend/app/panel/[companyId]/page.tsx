import { Suspense } from "react";

import { Skeleton } from "@heroui/react";

import CompanyPanelPageClient from "./CompanyPanelPageClient";

// The panel loads the selected company in the browser, so the route shell cannot contain
// that data; allow the segment to wait for its rendered UI during prerendering.
export const instant = false;

export default async function CompanyPanelPage({
  params,
}: {
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = await params;
  return (
    <Suspense fallback={<Skeleton className="h-[240px] rounded-[var(--radius)]" />}>
      <CompanyPanelPageClient companyId={companyId} />
    </Suspense>
  );
}
