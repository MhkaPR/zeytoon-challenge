"use client";

import { Card, Chip, Skeleton, Typography } from "@heroui/react";
import NextLink from "next/link";

import { useOpsData } from "@/src/features/ops/useOpsData";
import { listSites } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";

const STATE_LABEL: Record<string, string> = {
  onboarding: opsStrings.stateOnboarding,
  active: opsStrings.stateActive,
  suspended: opsStrings.stateSuspended,
};

export default function OpsSitesPage() {
  const { data, loading, error } = useOpsData(listSites, "sites");

  return (
    <main className="flex flex-col gap-[20px]">
      <div className="flex flex-col gap-[4px]">
        <Typography className="text-[20px] font-semibold" type="h2">
          {opsStrings.sitesTitle}
        </Typography>
        <Typography className="text-[13px] text-muted">{opsStrings.siteIntro}</Typography>
      </div>

      {loading ? (
        <Skeleton className="h-[200px] rounded-[var(--radius)]" />
      ) : error || !data ? (
        <Typography role="alert">{error ?? opsStrings.genericError}</Typography>
      ) : data.results.length === 0 ? (
        <Typography className="text-[13px] text-muted" role="status">
          {opsStrings.sitesEmpty}
        </Typography>
      ) : (
        <div className="grid gap-[12px] sm:grid-cols-2">
          {data.results.map((site) => (
            <Card className="flex flex-col gap-[10px] p-[18px]" key={site.id} variant="default">
              <div className="flex flex-wrap items-center justify-between gap-[8px]">
                <Typography className="text-[15px] font-semibold" dir="ltr">
                  {site.domain}
                </Typography>
                <Chip
                  color={
                    site.maintenance_state === "active"
                      ? "success"
                      : site.maintenance_state === "suspended"
                        ? "danger"
                        : "warning"
                  }
                  size="sm"
                  variant="soft"
                >
                  {STATE_LABEL[site.maintenance_state] ?? site.maintenance_state}
                </Chip>
              </div>
              <Typography className="text-[12px] text-muted">
                {opsStrings.linksCount}: {site.links_count}
              </Typography>
              <div className="flex flex-wrap gap-[8px]">
                <NextLink
                  className="rounded-[var(--radius)] bg-accent px-[12px] py-[6px] text-[13px] text-accent-foreground"
                  href={`/ops/sites/${site.id}`}
                >
                  {opsStrings.openSite}
                </NextLink>
                <NextLink
                  className="rounded-[var(--radius)] bg-surface-secondary px-[12px] py-[6px] text-[13px]"
                  href={`/ops/sites/${site.id}/links`}
                >
                  {opsStrings.openLinks}
                </NextLink>
              </div>
            </Card>
          ))}
        </div>
      )}
    </main>
  );
}
