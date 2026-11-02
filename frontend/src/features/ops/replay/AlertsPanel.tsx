"use client";

import { Button, Card, Typography } from "@heroui/react";
import { RefreshCw } from "lucide-react";

import type { FailureAlert } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";

import { FailureRateBadge } from "./FailureRateBadge";

export function AlertsPanel({
  alerts,
  threshold = 0.2,
  busyLinkId,
  onRerun,
}: {
  alerts: FailureAlert[];
  threshold?: number;
  busyLinkId?: number | null;
  onRerun: (linkId: number) => void;
}) {
  return (
    <div className="flex flex-col gap-[12px]">
      <Typography className="text-[13px] text-muted">{opsStrings.alertsIntro}</Typography>
      {alerts.length === 0 ? (
        <Typography className="text-[13px] text-muted" role="status">
          {opsStrings.noAlerts}
        </Typography>
      ) : (
        alerts.map((alert) => (
          <Card className="flex flex-col gap-[10px] p-[16px]" key={alert.id} variant="default">
            <div className="flex flex-wrap items-center justify-between gap-[8px]">
              <Typography className="text-[14px] font-semibold">
                Link #{alert.link_id}
              </Typography>
              <FailureRateBadge rate={alert.failure_rate} threshold={threshold} />
            </div>
            <Typography className="text-[12px] text-muted">
              {opsStrings.status}: {alert.state} · {opsStrings.lastReplay}:{" "}
              {alert.raised_at ?? opsStrings.none}
            </Typography>
            <Button
              className="self-start"
              isDisabled={busyLinkId === alert.link_id}
              onPress={() => onRerun(alert.link_id)}
              size="sm"
              variant="secondary"
            >
              <RefreshCw aria-hidden className="size-4" />
              {busyLinkId === alert.link_id ? opsStrings.rerunning : opsStrings.rerun}
            </Button>
          </Card>
        ))
      )}
    </div>
  );
}
