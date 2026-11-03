"use client";

import { useTranslations } from "next-intl";
import {
  Button,
  Card,
  Chip,
  Input,
  Label,
  Separator,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@heroui/react";
import { Upload, Video } from "lucide-react";
import { useState } from "react";

import { useSiteConfig } from "@/src/features/site/SiteConfigProvider";
import type { CaptureSession } from "@/src/lib/api/ops";
import type { DomtrackHealth } from "@/src/lib/api/ops";
import { StageBadge } from "../pipeline/StageBadge";

export type CaptureMode = "interactive" | "fixed_duration";

export function CapturePanel({
  stage,
  capture,
  traceStored,
  busy = false,
  errorCode,
  onStart,
  onUpload,
  onLoadLocal,
  onFail,
  onContinue,
  onRecheck,
  domtrack,
  activeCapture,
}: {
  stage: string;
  capture: CaptureSession | null;
  traceStored: boolean;
  busy?: boolean;
  errorCode?: string | null;
  onStart: (mode: CaptureMode, durationMs?: number) => void;
  onUpload: (file: File) => void;
  onLoadLocal: () => void;
  onFail: () => void;
  onContinue: () => void;
  onRecheck: () => void;
  domtrack?: DomtrackHealth | null;
  activeCapture?: CaptureSession | null;
}) {
  const ot = useTranslations();
  const config = useSiteConfig();
  const defaultDuration = config.ops.captureDefaultDurationMs;
  const [mode, setMode] = useState<CaptureMode>("interactive");
  const [duration, setDuration] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const effectiveDuration = duration ?? String(defaultDuration);

  return (
    <div className="flex flex-col gap-[20px]">
      <div className="flex flex-wrap items-center gap-[8px]">
        <StageBadge stage={stage} />
        <Typography
          className={`text-[13px] ${traceStored ? "text-success" : "text-warning"}`}
          role="status"
        >
          {traceStored ? ot("traceStored") : ot("traceMissing")}
        </Typography>
      </div>

      <Card className="flex flex-col gap-[16px] p-[20px]" variant="default">
        <Typography className="text-[13px] text-muted">{ot("captureIntro")}</Typography>

        <div className="flex flex-wrap items-center gap-[8px] text-[12px]">
          <Chip
            color={domtrack?.reachable ? "success" : "danger"}
            variant="soft"
          >
            {domtrack?.reachable
              ? ot("domtrackConnected")
              : ot("domtrackDisconnected")}
          </Chip>
          <span className="text-muted" dir="ltr">
            {domtrack?.base_url ?? ""}
          </span>
          <Button size="sm" variant="ghost" onPress={onRecheck}>
            {ot("domtrackRecheck")}
          </Button>
        </div>
        {domtrack && !domtrack.reachable && (
          <Typography className="text-[12px] text-warning" role="status">
            {ot("domtrackHint")}
          </Typography>
        )}
        {activeCapture && (
          <Typography className="text-[13px] text-warning" role="status">
            {ot("captureInProgress")}
          </Typography>
        )}

        <div className="flex flex-col gap-[6px]">
          <Typography className="text-[12px] text-muted">{ot("mode")}</Typography>
          <ToggleButtonGroup
            aria-label={ot("mode")}
            isDetached
            selectedKeys={[mode]}
            selectionMode="single"
            onSelectionChange={(keys) => {
              const next = [...keys][0];
              if (next === "interactive" || next === "fixed_duration") setMode(next);
            }}
          >
            <ToggleButton id="interactive">{ot("modeInteractive")}</ToggleButton>
            <ToggleButton id="fixed_duration">{ot("modeFixed")}</ToggleButton>
          </ToggleButtonGroup>
        </div>

        {mode === "fixed_duration" && (
          <TextField name="duration" value={effectiveDuration} onChange={setDuration}>
            <Label>{ot("durationMs")}</Label>
            <Input inputMode="numeric" />
          </TextField>
        )}
        <Typography className="text-[11px] text-muted">
          {mode === "fixed_duration"
            ? ot("captureWindowHint")
            : ot("captureInteractiveHint")}
        </Typography>

        <div className="flex flex-wrap gap-[8px]">
          <Button
            isDisabled={busy || Boolean(activeCapture)}
            onPress={() =>
              onStart(
                mode,
                mode === "fixed_duration" ? Number(effectiveDuration) || defaultDuration : undefined,
              )
            }
          >
            <Video aria-hidden className="size-4" />
            {busy ? ot("starting") : ot("startCapture")}
          </Button>
          {capture && (
            <Button isDisabled={busy} onPress={onFail} variant="danger-soft">
              {ot("failCapture")}
            </Button>
          )}
        </div>
        <Typography className="text-[11px] text-muted">
          {ot("captureOneAtATime")}
        </Typography>

        {errorCode === "domtrack_unreachable" && (
          <Typography className="text-[13px] text-danger" role="alert">
            {ot("domtrackUnreachable")}
          </Typography>
        )}
      </Card>

      {capture && (
        <Card className="flex flex-col gap-[12px] p-[20px]" variant="secondary">
          <Separator />
          <Typography className="text-[15px] font-semibold" type="h3">
            {ot("manualUploadTitle")}
          </Typography>
          <Typography className="text-[12px] text-muted">
            {ot("manualUploadHint")}
          </Typography>
          {capture.local_path && (
            <Typography className="text-[12px] text-muted" dir="ltr">
              {ot("localPath")}: {capture.local_path}
            </Typography>
          )}
          <input
            aria-label={ot("uploadTrace")}
            className="text-[13px]"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            type="file"
          />
          <Button
            className="self-start"
            isDisabled={busy || file === null}
            onPress={() => file && onUpload(file)}
            variant="secondary"
          >
            <Upload aria-hidden className="size-4" />
            {busy ? ot("uploading") : ot("uploadTrace")}
          </Button>
          {capture?.local_path && (
            <Button
              className="self-start"
              isDisabled={busy}
              onPress={onLoadLocal}
              variant="secondary"
            >
              <Upload aria-hidden className="size-4" />
              {ot("loadLocalTrace")}
            </Button>
          )}
        </Card>
      )}

      <div className="flex flex-wrap items-center gap-[8px]">
        <Button
          isDisabled={!traceStored}
          onPress={onContinue}
          variant={traceStored ? "primary" : "secondary"}
        >
          {traceStored ? ot("continueToTables") : ot("advanceBlocked")}
        </Button>
        {capture?.trace_id && (
          <Typography className="text-[12px] text-muted">
            {ot("traceId")}: {capture.trace_id}
          </Typography>
        )}
      </div>
    </div>
  );
}
