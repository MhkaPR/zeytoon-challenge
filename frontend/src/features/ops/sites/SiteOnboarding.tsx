"use client";

import { Card, Chip, Separator, Typography } from "@heroui/react";
import { Globe, Workflow } from "lucide-react";

import type { Site } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";

const STATE_LABEL: Record<string, string> = {
  onboarding: opsStrings.stateOnboarding,
  active: opsStrings.stateActive,
  suspended: opsStrings.stateSuspended,
};

export function SiteOnboarding({
  site,
  linksCount,
}: {
  site: Site;
  linksCount: number;
}) {
  return (
    <Card className="flex flex-col gap-[16px] p-[20px]" variant="default">
      <div className="flex flex-wrap items-center justify-between gap-[12px]">
        <div className="flex items-center gap-[10px]">
          <span className="flex size-[40px] items-center justify-center rounded-full bg-accent-soft text-accent">
            <Globe aria-hidden className="size-5" />
          </span>
          <div className="flex flex-col gap-[2px]">
            <Typography className="text-[17px] font-semibold" type="h3" dir="ltr">
              {site.domain}
            </Typography>
            <span className="text-[12px] text-muted">
              {opsStrings.linksCount}: {linksCount}
            </span>
          </div>
        </div>
        <Chip color={site.maintenance_state === "active" ? "success" : "warning"} variant="soft">
          {STATE_LABEL[site.maintenance_state] ?? site.maintenance_state}
        </Chip>
      </div>
      <Separator />
      <div className="flex items-start gap-[10px]">
        <Workflow aria-hidden className="mt-[2px] size-4 text-accent" />
        <Typography className="text-[13px] text-muted">
          {opsStrings.automaticPipelineHint}
        </Typography>
      </div>
    </Card>
  );
}
