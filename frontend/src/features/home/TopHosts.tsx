import { Card, Chip, Typography } from "@heroui/react";
import NextLink from "next/link";

import { strings, topHosts } from "@/src/lib/i18n/strings";

/**
 * Highest-ranked hosts, sorted by rank. Each row is a card linking to the provider; the
 * rank is shown as plain text so the ordering does not rely on color alone.
 */
export function TopHosts() {
  return (
    <section className="flex flex-col gap-[24px]">
      <div className="flex flex-col gap-[8px]">
        <Typography className="text-[28px] font-semibold" type="h2">
          {strings.topHostsTitle}
        </Typography>
        <Typography className="max-w-[720px] leading-[1.8]" color="muted">
          {strings.topHostsIntro}
        </Typography>
      </div>

      <div className="grid grid-cols-1 gap-[16px] sm:grid-cols-2">
        {topHosts.map((host) => (
          <NextLink
            key={host.domain}
            className="rounded-[var(--radius)] focus-visible:outline-none"
            href={`/companies/${encodeURIComponent(host.domain)}`}
          >
            <Card
              className="flex h-full flex-row items-center gap-[16px] p-[20px] transition-shadow hover:shadow-overlay"
              variant="secondary"
            >
              <span
                aria-hidden
                className="flex size-[36px] shrink-0 items-center justify-center rounded-full bg-accent font-mono text-[15px] font-medium text-accent-foreground"
              >
                {host.rank}
              </span>
              <div className="flex flex-1 flex-col gap-[4px]">
                <Card.Title>{host.name}</Card.Title>
                <Typography className="text-[12px]" type="code">
                  {host.domain}
                </Typography>
                <Typography color="muted" type="body-sm">
                  {`${strings.topHostsLocationLabel}: ${host.location}`}
                </Typography>
              </div>
              <div className="flex flex-col items-end gap-[8px]">
                <Chip color="accent" size="sm" variant="soft">
                  {host.service}
                </Chip>
                <Typography className="font-mono text-[13px] font-medium">
                  {`${strings.rankingScoreLabel} ${host.score}`}
                </Typography>
              </div>
            </Card>
          </NextLink>
        ))}
      </div>
    </section>
  );
}
