"use client";

import { Button, Skeleton, Typography } from "@heroui/react";
import { ArrowRight } from "lucide-react";
import NextLink from "next/link";
import { use, useEffect, useState } from "react";

import { LinkList } from "@/src/features/ops/links/LinkList";
import { useOpsData } from "@/src/features/ops/useOpsData";
import { discoverLinks, getSiteLinks } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";
import { getAccessToken } from "@/src/lib/session";

export default function OpsSiteLinksPageClient({
  params,
}: {
  params: Promise<{ siteId: string }>;
}) {
  const { siteId } = use(params);
  const id = Number(siteId);
  const { data, loading, error, reload } = useOpsData(
    (token) => getSiteLinks(token, id),
    String(id),
  );
  const [discovering, setDiscovering] = useState(false);
  const [discoverMessage, setDiscoverMessage] = useState("");
  useEffect(() => {
    const interval = window.setInterval(reload, 5000);
    return () => window.clearInterval(interval);
  }, [reload]);

  async function discoverNewLinks() {
    const token = getAccessToken();
    if (!token) return;
    setDiscovering(true);
    setDiscoverMessage("");
    try {
      const result = await discoverLinks(token, id);
      setDiscoverMessage(`${result.candidates.length} لینک تازه پیدا شد؛ پردازش در صف قرار گرفت.`);
      await reload();
    } catch {
      setDiscoverMessage(opsStrings.genericError);
    } finally {
      setDiscovering(false);
    }
  }

  return (
    <main className="flex flex-col gap-[20px]">
      <NextLink
        className="flex w-fit items-center gap-[6px] text-[13px] font-medium text-muted hover:text-foreground"
        href={`/ops/sites/${id}`}
      >
        <ArrowRight aria-hidden className="size-4" />
        {opsStrings.backToSite}
      </NextLink>
      <div className="flex flex-col gap-[4px]">
        <Typography className="text-[20px] font-semibold" type="h2">
          {opsStrings.linksTitle}
        </Typography>
        <Typography className="text-[13px] text-muted">
          {opsStrings.automaticPipelineHint}
        </Typography>
      </div>
      <div className="flex flex-wrap items-center gap-[12px]">
        <Button isDisabled={discovering} onPress={discoverNewLinks}>
          {discovering ? "در حال بررسی دامنه…" : opsStrings.discoverLinks}
        </Button>
        {discoverMessage && <Typography role="status" type="body-sm">{discoverMessage}</Typography>}
      </div>
      {!data ? (
        loading ? (
          <Skeleton className="h-[220px] rounded-[var(--radius)]" />
        ) : (
          <Typography role="alert">{error ?? opsStrings.genericError}</Typography>
        )
      ) : (
        <>
          {error && <Typography role="alert">{error}</Typography>}
          <LinkList links={data.links} />
        </>
      )}
    </main>
  );
}
