"use client";

import {
  Button,
  Card,
  Chip,
  Label,
  Separator,
  TextArea,
  TextField,
  Typography,
} from "@heroui/react";
import { Globe, Link2, RefreshCw } from "lucide-react";
import { useState } from "react";

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
  busy = false,
  onDiscover,
  onManualAdd,
}: {
  site: Site;
  linksCount: number;
  busy?: boolean;
  onDiscover: () => void;
  onManualAdd: (urls: string[]) => void;
}) {
  const [manual, setManual] = useState("");

  function submitManual() {
    const urls = manual
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    if (urls.length === 0) return;
    onManualAdd(urls);
    setManual("");
  }

  return (
    <div className="flex flex-col gap-[20px]">
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

        <Typography className="text-[13px] text-muted">
          {site.has_sitemap ? opsStrings.sitemapFound : opsStrings.sitemapMissing}
        </Typography>

        {site.has_sitemap && (
          <Button isDisabled={busy} onPress={onDiscover} variant="secondary">
            <RefreshCw aria-hidden className="size-4" />
            {busy ? opsStrings.discovering : opsStrings.discoverLinks}
          </Button>
        )}
      </Card>

      <Card className="flex flex-col gap-[12px] p-[20px]" variant="secondary">
        <div className="flex items-center gap-[6px]">
          <Link2 aria-hidden className="size-4 text-muted" />
          <Typography className="text-[15px] font-semibold" type="h3">
            {opsStrings.manualLinksTitle}
          </Typography>
        </div>
        <Typography className="text-[12px] text-muted">{opsStrings.manualLinksHint}</Typography>
        <TextField name="manual-links" value={manual} onChange={setManual}>
          <Label>{opsStrings.manualLinksTitle}</Label>
          <TextArea placeholder={opsStrings.manualLinksPlaceholder} rows={3} />
        </TextField>
        <Button
          className="self-start"
          isDisabled={busy || manual.trim().length === 0}
          onPress={submitManual}
          variant="secondary"
        >
          {busy ? opsStrings.addingLinks : opsStrings.addLinks}
        </Button>
      </Card>
    </div>
  );
}
