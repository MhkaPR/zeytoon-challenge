"use client";

import { Skeleton, Typography } from "@heroui/react";
import { use, useState } from "react";

import { LinkStageNav } from "@/src/features/ops/pipeline/LinkStageNav";
import { TableList } from "@/src/features/ops/tables/TableList";
import { opsErrorMessage, useOpsData } from "@/src/features/ops/useOpsData";
import { AuthApiError } from "@/src/lib/api/auth";
import { extractTables, getSettings, getTables, labelTables } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";
import { getAccessToken } from "@/src/lib/session";

export default function OpsTablesPage({
  params,
}: {
  params: Promise<{ linkId: string }>;
}) {
  const { linkId } = use(params);
  const id = Number(linkId);
  const { data, loading, error, reload } = useOpsData(
    (token) => getTables(token, id),
    String(id),
  );
  const settings = useOpsData(getSettings, "labeling");
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
      if (err instanceof AuthApiError && err.code === "labeling_disabled") {
        setFailure(opsStrings.labelingDisabled);
      } else {
        setFailure(opsErrorMessage(err));
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex flex-col gap-[20px]">
      <div className="flex flex-col gap-[4px]">
        <Typography className="text-[20px] font-semibold" type="h2">
          {opsStrings.tablesTitle}
        </Typography>
        <Typography className="text-[13px] text-muted">{opsStrings.tablesIntro}</Typography>
        <LinkStageNav active="tables" linkId={id} />
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
        <Skeleton className="h-[240px] rounded-[var(--radius)]" />
      ) : error || !data ? (
        <Typography role="alert">{error ?? opsStrings.genericError}</Typography>
      ) : (
        <TableList
          busy={busy}
          labelingEnabled={Boolean(settings.data?.LABELING_ENABLED)}
          onExtract={() =>
            run(() => extractTables(getAccessToken(), id), opsStrings.extracting)
          }
          onLabel={() => run(() => labelTables(getAccessToken(), id), opsStrings.labelingDone)}
          stage={data.pipeline_stage}
          tables={data.tables}
          traceStored={data.current_trace_id !== null}
        />
      )}
    </main>
  );
}
