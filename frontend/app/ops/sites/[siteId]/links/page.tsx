"use client";

import { Skeleton, Typography } from "@heroui/react";
import { ArrowRight } from "lucide-react";
import NextLink from "next/link";
import { use, useState } from "react";

import { LinkReviewTable } from "@/src/features/ops/links/LinkReviewTable";
import { opsErrorMessage, useOpsData } from "@/src/features/ops/useOpsData";
import { getSiteLinks, reviewLinks } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";
import { getAccessToken } from "@/src/lib/session";

export default function OpsSiteLinksPage({
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
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  async function submit(keepIds: number[], removeIds: number[]) {
    setBusy(true);
    setFailure(null);
    setNotice(null);
    try {
      await reviewLinks(getAccessToken(), id, keepIds, removeIds);
      setNotice(opsStrings.linksSaved);
      reload();
    } catch (err) {
      setFailure(opsErrorMessage(err));
    } finally {
      setBusy(false);
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
        <Typography className="text-[13px] text-muted">{opsStrings.linksIntro}</Typography>
      </div>

      {notice && (
        <Typography className="text-[13px] text-success" role="status">
          {notice}
        </Typography>
      )}
      {failure && (
        <Typography className="text-[13px] text-danger" role="alert">
          {failure}
        </Typography>
      )}

      {loading ? (
        <Skeleton className="h-[220px] rounded-[var(--radius)]" />
      ) : error || !data ? (
        <Typography role="alert">{error ?? opsStrings.genericError}</Typography>
      ) : (
        <LinkReviewTable busy={busy} links={data.links} onReview={submit} />
      )}
    </main>
  );
}
