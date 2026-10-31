"use client";

import { Skeleton, Typography } from "@heroui/react";
import { ArrowRight } from "lucide-react";
import NextLink from "next/link";
import { use, useEffect } from "react";

import { LinkList } from "@/src/features/ops/links/LinkList";
import { SiteOnboarding } from "@/src/features/ops/sites/SiteOnboarding";
import { useOpsData } from "@/src/features/ops/useOpsData";
import { getSite } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";

export default function OpsSitePageClient({
  params,
}: {
  params: Promise<{ siteId: string }>;
}) {
  const { siteId } = use(params);
  const id = Number(siteId);
  const { data, loading, error, reload } = useOpsData(
    (token) => getSite(token, id),
    String(id),
  );
  useEffect(() => {
    const interval = window.setInterval(reload, 8000);
    return () => window.clearInterval(interval);
  }, [reload]);

  return (
    <main className="flex flex-col gap-[20px]">
      <NextLink
        className="flex w-fit items-center gap-[6px] text-[13px] font-medium text-muted hover:text-foreground"
        href="/ops/sites"
      >
        <ArrowRight aria-hidden className="size-4" />
        {opsStrings.backToSites}
      </NextLink>
      <div className="flex flex-col gap-[4px]">
        <Typography className="text-[20px] font-semibold" type="h2">
          {opsStrings.siteTitle}
        </Typography>
        <Typography className="text-[13px] text-muted">{opsStrings.siteIntro}</Typography>
      </div>

      {loading ? (
        <Skeleton className="h-[220px] rounded-[var(--radius)]" />
      ) : error || !data ? (
        <Typography role="alert">{error ?? opsStrings.genericError}</Typography>
      ) : (
        <>
          <SiteOnboarding linksCount={data.links.length} site={data.site} />
          <LinkList links={data.links} />
        </>
      )}
    </main>
  );
}
