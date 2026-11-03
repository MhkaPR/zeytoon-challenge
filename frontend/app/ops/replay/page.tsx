"use client";

import { useTranslations } from "next-intl";
import { Button, Skeleton, Typography } from "@heroui/react";
import { Play } from "lucide-react";
import { useState } from "react";

import {
  AlertsPanel,
} from "@/src/features/ops/replay/AlertsPanel";
import { RecipientManager } from "@/src/features/ops/replay/RecipientManager";
import { ReplayRunsTable } from "@/src/features/ops/replay/ReplayRunsTable";
import { opsErrorMessage, useOpsData } from "@/src/features/ops/useOpsData";
import {
  addRecipient,
  createReplayRuns,
  deactivateRecipient,
  getSettings,
  listAlerts,
  listRecipients,
  listReplayRuns,
  rerunLink,
} from "@/src/lib/api/ops";
import { getAccessToken } from "@/src/lib/session";

export default function OpsReplayPage() {
  const ot = useTranslations();
  const runs = useOpsData((token) => listReplayRuns(token), "runs");
  const alerts = useOpsData((token) => listAlerts(token), "alerts");
  const recipients = useOpsData((token) => listRecipients(token), "recipients");
  const settings = useOpsData(getSettings, "failure-threshold");
  const [busy, setBusy] = useState(false);
  const [busyLinkId, setBusyLinkId] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true);
    setFailure(null);
    setNotice(null);
    try {
      await action();
      setNotice(success);
      runs.reload();
      alerts.reload();
      recipients.reload();
    } catch (err) {
      setFailure(opsErrorMessage(err, ot));
    } finally {
      setBusy(false);
    }
  }

  async function rerun(linkId: number) {
    setBusyLinkId(linkId);
    setFailure(null);
    setNotice(null);
    try {
      await rerunLink(getAccessToken(), linkId);
      setNotice(ot("rerunStarted"));
      runs.reload();
      alerts.reload();
    } catch (err) {
      setFailure(opsErrorMessage(err, ot));
    } finally {
      setBusyLinkId(null);
    }
  }

  const threshold = Number(settings.data?.FAILURE_RATE_THRESHOLD ?? 0.2);
  const loading = runs.loading || alerts.loading || recipients.loading;

  return (
    <main className="flex flex-col gap-[24px]">
      <div className="flex flex-col gap-[4px]">
        <Typography className="text-[20px] font-semibold" type="h2">
          {ot("replayTitle")}
        </Typography>
        <Typography className="text-[13px] text-muted">{ot("replayIntro")}</Typography>
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

      <div>
        <Button
          isDisabled={busy}
          onPress={() =>
            run(() => createReplayRuns(getAccessToken()), ot("running"))
          }
        >
          <Play aria-hidden className="size-4" />
          {busy ? ot("running") : ot("createReplays")}
        </Button>
      </div>

      {loading ? (
        <Skeleton className="h-[260px] rounded-[var(--radius)]" />
      ) : (
        <>
          <section className="flex flex-col gap-[10px]">
            <Typography className="text-[16px] font-semibold" type="h3">
              {ot("createReplays")}
            </Typography>
            <ReplayRunsTable runs={runs.data?.results ?? []} />
          </section>

          <section className="flex flex-col gap-[10px]">
            <Typography className="text-[16px] font-semibold" type="h3">
              {ot("alertsTitle")}
            </Typography>
            <AlertsPanel
              alerts={alerts.data?.results ?? []}
              busyLinkId={busyLinkId}
              onRerun={rerun}
              threshold={threshold}
            />
          </section>

          <section>
            <RecipientManager
              busy={busy || busyLinkId !== null}
              onAdd={(userId, name) =>
                run(
                  () => addRecipient(getAccessToken(), userId, name),
                  ot("settingsSaved"),
                )
              }
              onDeactivate={(recipientId) =>
                run(
                  () => deactivateRecipient(getAccessToken(), recipientId),
                  ot("settingsSaved"),
                )
              }
              recipients={recipients.data?.results ?? []}
            />
          </section>
        </>
      )}
    </main>
  );
}
