"use client";

import { Skeleton, Typography } from "@heroui/react";
import { ArrowRight } from "lucide-react";
import NextLink from "next/link";
import { use } from "react";

import { LinkList } from "@/src/features/ops/links/LinkList";
import { useOpsData } from "@/src/features/ops/useOpsData";
import { getSiteLinks } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";

export default function OpsSiteLinksPage({
  params,
}: {
  params: Promise<{ siteId: string }>;
}) {
  const { siteId } = use(params);
  const id = Number(siteId);
  const { data, loading, error } = useOpsData(
    (token) => getSiteLinks(token, id),
    String(id),
  );

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
      {loading ? (
        <Skeleton className="h-[220px] rounded-[var(--radius)]" />
      ) : error || !data ? (
        <Typography role="alert">{error ?? opsStrings.genericError}</Typography>
      ) : (
        <LinkList links={data.links} />
      )}
    </main>
  );
}
