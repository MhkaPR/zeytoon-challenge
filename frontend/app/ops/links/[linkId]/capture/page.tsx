"use client";

import { useTranslations } from "next-intl";
import { Skeleton, Typography } from "@heroui/react";
import { useRouter } from "next/navigation";
import { use, useState } from "react";

import { CapturePanel, type CaptureMode } from "@/src/features/ops/capture/CapturePanel";
import { LinkStageNav } from "@/src/features/ops/pipeline/LinkStageNav";
import { opsErrorMessage, useOpsData } from "@/src/features/ops/useOpsData";
import { AuthApiError } from "@/src/lib/api/auth";
import {
  failCapture,
  getActiveCapture,
  getDomtrackHealth,
  getTables,
  startCapture,
  uploadLocalTrace,
  uploadTrace,
  type CaptureSession,
} from "@/src/lib/api/ops";
import { getAccessToken } from "@/src/lib/session";

export default function OpsCapturePage({
  params,
}: {
  params: Promise<{ linkId: string }>;
}) {
  const ot = useTranslations("ops");
  const { linkId } = use(params);
  const id = Number(linkId);
  const router = useRouter();
  const { data, loading, error, reload } = useOpsData(
    (token) => getTables(token, id),
    String(id),
  );
  const [capture, setCapture] = useState<CaptureSession | null>(null);
  const [busy, setBusy] = useState(false);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const health = useOpsData(getDomtrackHealth, "domtrack-health");
  const active = useOpsData(getActiveCapture, `active-capture-${id}`);

  function fail(err: unknown) {
    setErrorCode(err instanceof AuthApiError ? err.code : null);
    setFailure(opsErrorMessage(err));
  }

  async function start(mode: CaptureMode, durationMs?: number) {
    setBusy(true);
    setFailure(null);
    setErrorCode(null);
    setNotice(null);
    try {
      const response = await startCapture(getAccessToken(), id, mode, durationMs);
      setCapture(response.capture);
      setNotice(ot("captureStarted"));
      reload();
      active.reload();
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function upload(file: File) {
    if (!capture) return;
    setBusy(true);
    setFailure(null);
    try {
      const response = await uploadTrace(getAccessToken(), capture.id, file);
      setCapture(response.capture);
      setNotice(ot("traceStored"));
      reload();
      active.reload();
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function loadLocal() {
    if (!capture?.local_path) return;
    setBusy(true);
    setFailure(null);
    try {
      const response = await uploadLocalTrace(
        getAccessToken(),
        capture.id,
        capture.local_path,
      );
      setCapture(response.capture);
      setNotice(ot("traceStored"));
      reload();
      active.reload();
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function markFailed() {
    if (!capture) return;
    setBusy(true);
    try {
      const response = await failCapture(
        getAccessToken(),
        capture.id,
        "operator failed",
      );
      setCapture((response as { capture: CaptureSession }).capture ?? capture);
      setFailure(ot("captureFailed"));
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  const traceStored = Boolean(data?.current_trace_id || capture?.trace_id);

  return (
    <main className="flex flex-col gap-[20px]">
      <div className="flex flex-col gap-[4px]">
        <Typography className="text-[20px] font-semibold" type="h2">
          {ot("captureTitle")}
        </Typography>
        <Typography className="text-[12px] text-muted" dir="ltr">
          {data?.url ?? ""}
        </Typography>
        <LinkStageNav active="capture" linkId={id} siteId={data?.site_id} />
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
        <Typography role="alert">{error ?? ot("genericError")}</Typography>
      ) : (
        <CapturePanel
          busy={busy}
          capture={capture}
          errorCode={errorCode}
          activeCapture={active.data?.capture ?? null}
          domtrack={health.data}
          onContinue={() => router.push(`/ops/links/${id}/tables`)}
          onFail={markFailed}
          onLoadLocal={loadLocal}
          onRecheck={health.reload}
          onStart={start}
          onUpload={upload}
          stage={data.pipeline_stage}
          traceStored={traceStored}
        />
      )}
    </main>
  );
}
