"use client";

import { useTranslations } from "next-intl";
import { Skeleton, Typography } from "@heroui/react";
import { ArrowRight } from "lucide-react";
import NextLink from "next/link";
import { use, useEffect } from "react";

import { LinkList } from "@/src/features/ops/links/LinkList";
import { SiteOnboarding } from "@/src/features/ops/sites/SiteOnboarding";
import { useSiteConfig } from "@/src/features/site/SiteConfigProvider";
import { useOpsData } from "@/src/features/ops/useOpsData";
import { getSite } from "@/src/lib/api/ops";
export default function OpsSitePageClient({
  params,
}: {
  params: Promise<{ siteId: string }>;
}) {
  const ot = useTranslations();
  const config = useSiteConfig();
  const { siteId } = use(params);
  const id = Number(siteId);
  const { data, loading, error, reload } = useOpsData(
    (token) => getSite(token, id),
    String(id),
  );
  useEffect(() => {
    const interval = window.setInterval(reload, config.ops.siteRefreshMs);
    return () => window.clearInterval(interval);
  }, [config.ops.siteRefreshMs, reload]);

  return (
    <main className="flex flex-col gap-[20px]">
      <NextLink
        className="flex w-fit items-center gap-[6px] text-[13px] font-medium text-muted hover:text-foreground"
        href="/ops/sites"
      >
        <ArrowRight aria-hidden className="size-4" />
        {ot("backToSites")}
      </NextLink>
      <div className="flex flex-col gap-[4px]">
        <Typography className="text-[20px] font-semibold" type="h2">
          {ot("siteTitle")}
        </Typography>
        <Typography className="text-[13px] text-muted">{ot("siteIntro")}</Typography>
      </div>

      {!data ? (
        loading ? (
          <Skeleton className="h-[220px] rounded-[var(--radius)]" />
        ) : (
          <Typography role="alert">{error ?? ot("genericError")}</Typography>
        )
      ) : (
        <>
          {error && <Typography role="alert">{error}</Typography>}
          <SiteOnboarding linksCount={data.links.length} site={data.site} />
          <LinkList links={data.links} />
        </>
      )}
    </main>
  );
}
