"use client";

import { useTranslations } from "next-intl";
import { Card, Chip, Separator, Typography } from "@heroui/react";
import { Globe, Workflow } from "lucide-react";

import type { Site } from "@/src/lib/api/ops";
const STATE_LABEL_KEY: Record<string, string> = {
  onboarding: "stateOnboarding",
  active: "stateActive",
  suspended: "stateSuspended",
};

export function SiteOnboarding({
  site,
  linksCount,
}: {
  site: Site;
  linksCount: number;
}) {
  const ot = useTranslations();
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
              {ot("linksCount")}: {linksCount}
            </span>
          </div>
        </div>
        <Chip color={site.maintenance_state === "active" ? "success" : "warning"} variant="soft">
          {ot(STATE_LABEL_KEY[site.maintenance_state] ?? "") || site.maintenance_state}
        </Chip>
      </div>
      <Separator />
      <div className="flex items-start gap-[10px]">
        <Workflow aria-hidden className="mt-[2px] size-4 text-accent" />
        <Typography className="text-[13px] text-muted">
          {ot("automaticPipelineHint")}
        </Typography>
      </div>
    </Card>
  );
}
