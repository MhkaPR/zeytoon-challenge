"use client";

import { useTranslations } from "next-intl";
import { Card, Chip, Typography } from "@/src/features/ui/heroUi";
import { ChevronLeft, MapPin, Star } from "lucide-react";
import NextLink from "next/link";

/**
 * Highest-ranked hosts, sorted by rank. Each row is a card linking to the provider; the
 * rank is shown as plain text so the ordering does not rely on color alone.
 */
export function TopHosts() {
  const ot = useTranslations();
  const topHosts = ot.raw("topHosts") as Array<{ rank: string; name: string; domain: string; score: string; location: string; service: string }>;
  return (
    <section className="flex flex-col gap-[24px]">
      <div className="flex flex-col gap-[8px]">
        <Typography className="text-[28px] font-semibold" type="h2">
          {ot("topHostsTitle")}
        </Typography>
        <Typography className="max-w-[720px] leading-[1.8]" color="muted">
          {ot("topHostsIntro")}
        </Typography>
      </div>

      <div className="grid grid-cols-1 gap-[16px] sm:grid-cols-2">
        {topHosts.map((host) => (
          <NextLink
            key={host.domain}
            href={`/companies/${encodeURIComponent(host.domain)}`}
            className="group block rounded-[var(--radius)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--background)]"
          >
            <Card
              className="flex h-full flex-col gap-[14px] p-[20px] transition-all duration-200 group-hover:-translate-y-[1px] group-hover:shadow-overlay"
              variant="default"
            >
              {/* Row 1 — identity */}
              <div className="flex items-center gap-[12px]">
                <span
                  aria-hidden
                  className="flex size-[36px] shrink-0 items-center justify-center rounded-full bg-accent font-mono text-[15px] font-semibold text-accent-foreground"
                >
                  {host.rank}
                </span>

                <div className="flex min-w-0 flex-1 flex-col gap-[2px]">
                  <Card.Title className="truncate">{host.name}</Card.Title>
                  <Typography
                    className="truncate text-[12px]"
                    type="code"
                    color="muted"
                  >
                    {host.domain}
                  </Typography>
                </div>

                <Chip
                  color="accent"
                  size="sm"
                  variant="soft"
                  className="shrink-0"
                >
                  {host.service}
                </Chip>
              </div>

              {/* Row 2 — meta */}
              <div className="flex items-center justify-between gap-[8px] border-t border-[var(--separator)] pt-[12px]">
                <div className="flex min-w-0 items-center gap-[6px]">
                  <MapPin aria-hidden className="size-[13px] shrink-0 text-muted" />
                  <Typography
                    className="truncate text-[12px]"
                    type="body-xs"
                    color="muted"
                  >
                    {host.location}
                  </Typography>
                </div>

                <div className="flex shrink-0 items-center gap-[10px]">
                  <div className="flex items-center gap-[4px]">
                    <Star
                      aria-hidden
                      className="size-[12px] fill-[var(--accent)] text-[var(--accent)]"
                    />
                    <Typography className="font-mono text-[12px] font-medium">
                      {host.score}
                    </Typography>
                    <span className="sr-only">{ot("rankingScoreLabel")}</span>
                  </div>

                  <ChevronLeft
                    aria-hidden
                    className="size-[16px] text-muted transition-transform duration-200 group-hover:-translate-x-[2px]"
                  />
                </div>
              </div>
            </Card>
          </NextLink>
        ))}
      </div>
    </section>
  );
}
