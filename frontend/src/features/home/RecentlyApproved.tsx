import { Card, Chip, Typography } from "@heroui/react";
import NextLink from "next/link";

import { recentlyApproved, strings } from "@/src/lib/i18n/strings";

/** Providers recently verified or approved, with when they were added (homepage). */
export function RecentlyApproved() {
  return (
    <section className="flex flex-col gap-[24px]">
      <div className="flex flex-col gap-[8px]">
        <Typography className="text-[28px] font-semibold" type="h2">
          {strings.recentlyApprovedTitle}
        </Typography>
        <Typography className="max-w-[720px] leading-[1.8]" color="muted">
          {strings.recentlyApprovedIntro}
        </Typography>
      </div>

      <Card className="flex flex-col gap-[4px] p-[8px]" variant="secondary">
        {recentlyApproved.map((item) => (
          <NextLink
            key={item.domain}
            className="flex flex-row items-center gap-[12px] rounded-[var(--radius)] p-[12px] hover:bg-surface-tertiary focus-visible:outline-none"
            href={`/companies/${encodeURIComponent(item.domain)}`}
          >
            <div className="flex flex-1 flex-col gap-[2px]">
              <Typography className="font-medium">{item.name}</Typography>
              <Typography className="text-[12px]" color="muted" type="code">
                {item.domain}
              </Typography>
            </div>
            <Chip color="accent" size="sm" variant="soft">
              {item.service}
            </Chip>
            <Typography className="text-[12px]" color="muted" type="body-xs">
              {item.time}
            </Typography>
          </NextLink>
        ))}
      </Card>
    </section>
  );
}
