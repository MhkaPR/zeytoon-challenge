"use client";

import { Skeleton, Typography } from "@heroui/react";
import NextLink from "next/link";
import { use } from "react";
import { useState } from "react";

import { SiteOnboarding } from "@/src/features/ops/sites/SiteOnboarding";
import { opsErrorMessage, useOpsData } from "@/src/features/ops/useOpsData";
import { addManualLinks, discoverLinks, getSite } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";
import { getAccessToken } from "@/src/lib/session";

export default function OpsSitePage({ params }: { params: Promise<{ siteId: string }> }) {
  const { siteId } = use(params);
  const id = Number(siteId);
  const { data, loading, error, reload } = useOpsData(
    (token) => getSite(token, id),
    String(id),
  );
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true);
    setFailure(null);
    setNotice(null);
    try {
      await action();
      setNotice(success);
      reload();
    } catch (err) {
      setFailure(opsErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex flex-col gap-[20px]">
      <div className="flex flex-col gap-[4px]">
        <Typography className="text-[20px] font-semibold" type="h2">
          {opsStrings.siteTitle}
        </Typography>
        <Typography className="text-[13px] text-muted">{opsStrings.siteIntro}</Typography>
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
        <>
          <SiteOnboarding
            busy={busy}
            linksCount={data.links.length}
            onDiscover={() =>
              run(
                () => discoverLinks(getAccessToken(), id),
                opsStrings.discoverDone,
              )
            }
            onManualAdd={(urls) =>
              run(
                () => addManualLinks(getAccessToken(), id, urls),
                opsStrings.linksSaved,
              )
            }
            site={data.site}
          />
          <div className="flex flex-wrap gap-[8px]">
            <NextLink
              className="rounded-[var(--radius)] bg-accent px-[14px] py-[8px] text-[14px] font-medium text-accent-foreground"
              href={`/ops/sites/${id}/links`}
            >
              {opsStrings.openLinks}
            </NextLink>
          </div>
        </>
      )}
    </main>
  );
}
