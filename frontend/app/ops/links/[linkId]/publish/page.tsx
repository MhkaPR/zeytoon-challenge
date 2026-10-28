"use client";

import { Skeleton, Typography } from "@heroui/react";
import { use, useState } from "react";

import { LinkStageNav } from "@/src/features/ops/pipeline/LinkStageNav";
import { CleaningPanel } from "@/src/features/ops/publishing/CleaningPanel";
import { opsErrorMessage, useOpsData } from "@/src/features/ops/useOpsData";
import {
  cleanLink,
  getRecipe,
  publishLink,
  type CleaningResult,
  type PublishResult,
} from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";
import { getAccessToken } from "@/src/lib/session";

export default function OpsPublishPage({
  params,
}: {
  params: Promise<{ linkId: string }>;
}) {
  const { linkId } = use(params);
  const id = Number(linkId);
  const { data, loading, error, reload } = useOpsData(
    (token) => getRecipe(token, id),
    String(id),
  );
  const [cleaning, setCleaning] = useState<CleaningResult | null>(null);
  const [published, setPublished] = useState<PublishResult | null>(null);
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
          {opsStrings.publishingTitle}
        </Typography>
        <Typography className="text-[13px] text-muted">{opsStrings.publishingIntro}</Typography>
        <LinkStageNav active="publish" linkId={id} />
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
        <Skeleton className="h-[260px] rounded-[var(--radius)]" />
      ) : error || !data ? (
        <Typography role="alert">{error ?? opsStrings.genericError}</Typography>
      ) : (
        <CleaningPanel
          busy={busy}
          cleaning={cleaning}
          onClean={() =>
            run(async () => {
              const result = await cleanLink(getAccessToken(), id);
              setCleaning(result);
            }, opsStrings.cleaningDone)
          }
          onPublish={() =>
            run(async () => {
              const result = await publishLink(getAccessToken(), id);
              setPublished(result);
            }, opsStrings.publishDone)
          }
          published={published}
          recipeReady={Boolean(data.recipe?.is_complete)}
          stage={data.pipeline_stage}
        />
      )}
    </main>
  );
}
