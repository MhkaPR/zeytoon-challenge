"use client";

import { useTranslations } from "next-intl";
import { buttonVariants, Card, Chip, Skeleton, Typography } from "@heroui/react";
import { ArrowRight, List } from "lucide-react";
import NextLink from "next/link";

import { useOpsData } from "@/src/features/ops/useOpsData";
import { listSites } from "@/src/lib/api/ops";
const STATE_LABEL_KEY: Record<string, string> = {
  onboarding: "stateOnboarding",
  active: "stateActive",
  suspended: "stateSuspended",
};

export default function OpsSitesPage() {
  const ot = useTranslations();
  const { data, loading, error } = useOpsData(listSites, "sites");

  return (
    <main className="flex flex-col gap-[20px]">
      <div className="flex flex-col gap-[4px]">
        <Typography className="text-[20px] font-semibold" type="h2">
          {ot("sitesTitle")}
        </Typography>
        <Typography className="text-[13px] text-muted">{ot("siteIntro")}</Typography>
      </div>

      {loading ? (
        <Skeleton className="h-[200px] rounded-[var(--radius)]" />
      ) : error || !data ? (
        <Typography role="alert">{error ?? ot("genericError")}</Typography>
      ) : data.results.length === 0 ? (
        <Typography className="text-[13px] text-muted" role="status">
          {ot("sitesEmpty")}
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
                  {ot(STATE_LABEL_KEY[site.maintenance_state] ?? "") || site.maintenance_state}
                </Chip>
              </div>
              <Typography className="text-[12px] text-muted">
                {ot("linksCount")}: {site.links_count}
              </Typography>
              <div className="flex flex-wrap gap-[8px]">
                <NextLink
                  className={buttonVariants({ size: "sm" })}
                  href={`/ops/sites/${site.id}`}
                >
                  <ArrowRight aria-hidden className="size-4" />
                  {ot("openSite")}
                </NextLink>
                <NextLink
                  className={buttonVariants({ size: "sm", variant: "secondary" })}
                  href={`/ops/sites/${site.id}/links`}
                >
                  <List aria-hidden className="size-4" />
                  {ot("openLinks")}
                </NextLink>
              </div>
            </Card>
          ))}
        </div>
      )}
    </main>
  );
}
