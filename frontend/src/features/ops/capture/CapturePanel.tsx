"use client";

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

import type { CaptureSession } from "@/src/lib/api/ops";
import type { DomtrackHealth } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";

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
  const [mode, setMode] = useState<CaptureMode>("interactive");
  const [duration, setDuration] = useState("30000");
  const [file, setFile] = useState<File | null>(null);

  return (
    <div className="flex flex-col gap-[20px]">
      <div className="flex flex-wrap items-center gap-[8px]">
        <StageBadge stage={stage} />
        <Typography
          className={`text-[13px] ${traceStored ? "text-success" : "text-warning"}`}
          role="status"
        >
          {traceStored ? opsStrings.traceStored : opsStrings.traceMissing}
        </Typography>
      </div>

      <Card className="flex flex-col gap-[16px] p-[20px]" variant="default">
        <Typography className="text-[13px] text-muted">{opsStrings.captureIntro}</Typography>

        <div className="flex flex-wrap items-center gap-[8px] text-[12px]">
          <Chip
            color={domtrack?.reachable ? "success" : "danger"}
            variant="soft"
          >
            {domtrack?.reachable
              ? opsStrings.domtrackConnected
              : opsStrings.domtrackDisconnected}
          </Chip>
          <span className="text-muted" dir="ltr">
            {domtrack?.base_url ?? ""}
          </span>
          <Button size="sm" variant="ghost" onPress={onRecheck}>
            {opsStrings.domtrackRecheck}
          </Button>
        </div>
        {domtrack && !domtrack.reachable && (
          <Typography className="text-[12px] text-warning" role="status">
            {opsStrings.domtrackHint}
          </Typography>
        )}
        {activeCapture && (
          <Typography className="text-[13px] text-warning" role="status">
            {opsStrings.captureInProgress}
          </Typography>
        )}

        <div className="flex flex-col gap-[6px]">
          <Typography className="text-[12px] text-muted">{opsStrings.mode}</Typography>
          <ToggleButtonGroup
            aria-label={opsStrings.mode}
            isDetached
            selectedKeys={[mode]}
            selectionMode="single"
            onSelectionChange={(keys) => {
              const next = [...keys][0];
              if (next === "interactive" || next === "fixed_duration") setMode(next);
            }}
          >
            <ToggleButton id="interactive">{opsStrings.modeInteractive}</ToggleButton>
            <ToggleButton id="fixed_duration">{opsStrings.modeFixed}</ToggleButton>
          </ToggleButtonGroup>
        </div>

        {mode === "fixed_duration" && (
          <TextField name="duration" value={duration} onChange={setDuration}>
            <Label>{opsStrings.durationMs}</Label>
            <Input inputMode="numeric" />
          </TextField>
        )}

        <div className="flex flex-wrap gap-[8px]">
          <Button
            isDisabled={busy || Boolean(activeCapture)}
            onPress={() =>
              onStart(
                mode,
                mode === "fixed_duration" ? Number(duration) || 30000 : undefined,
              )
            }
          >
            <Video aria-hidden className="size-4" />
            {busy ? opsStrings.starting : opsStrings.startCapture}
          </Button>
          {capture && (
            <Button isDisabled={busy} onPress={onFail} variant="danger-soft">
              {opsStrings.failCapture}
            </Button>
          )}
        </div>
        <Typography className="text-[11px] text-muted">
          {opsStrings.captureOneAtATime}
        </Typography>

        {errorCode === "domtrack_unreachable" && (
          <Typography className="text-[13px] text-danger" role="alert">
            {opsStrings.domtrackUnreachable}
          </Typography>
        )}
      </Card>

      {capture && (
        <Card className="flex flex-col gap-[12px] p-[20px]" variant="secondary">
          <Separator />
          <Typography className="text-[15px] font-semibold" type="h3">
            {opsStrings.manualUploadTitle}
          </Typography>
          <Typography className="text-[12px] text-muted">
            {opsStrings.manualUploadHint}
          </Typography>
          {capture.local_path && (
            <Typography className="text-[12px] text-muted" dir="ltr">
              {opsStrings.localPath}: {capture.local_path}
            </Typography>
          )}
          <input
            aria-label={opsStrings.uploadTrace}
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
            {busy ? opsStrings.uploading : opsStrings.uploadTrace}
          </Button>
          {capture?.local_path && (
            <Button
              className="self-start"
              isDisabled={busy}
              onPress={onLoadLocal}
              variant="secondary"
            >
              <Upload aria-hidden className="size-4" />
              {opsStrings.loadLocalTrace}
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
          {traceStored ? opsStrings.continueToTables : opsStrings.advanceBlocked}
        </Button>
        {capture?.trace_id && (
          <Typography className="text-[12px] text-muted">
            {opsStrings.traceId}: {capture.trace_id}
          </Typography>
        )}
      </div>
    </div>
  );
}
