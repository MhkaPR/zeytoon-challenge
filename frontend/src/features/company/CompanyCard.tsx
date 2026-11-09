import { Button, Card, Chip, Typography } from "@heroui/react";
import { useTranslations } from "next-intl";
import NextLink from "next/link";

import { CompanyLogo } from "./CompanyLogo";

/** Provider summary card used by the company directory and search surfaces. */
export function CompanyCard({
  name,
  domain,
  planCount = 0,
  description,
  serviceType,
}: {
  name: string;
  domain?: string;
  planCount?: number;
  description?: string;
  serviceType?: string;
}) {
  const ot = useTranslations();
  const href = domain ? `/companies/${encodeURIComponent(domain)}` : "/companies";

  return (
    <Card className="flex h-full flex-col gap-[16px] p-[20px]" variant="default">
      <div className="flex items-start gap-[12px]">
        <CompanyLogo domain={domain} name={name} />
        <div className="flex min-w-0 flex-1 flex-col gap-[4px]">
          <Card.Title className="truncate">{name}</Card.Title>
          {domain && (
            <NextLink
              className="w-fit text-[12px] text-muted transition-colors hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              dir="ltr"
              href={href}
            >
              {domain}
            </NextLink>
          )}
        </div>
        {serviceType && (
          <Chip color="accent" size="sm" variant="soft">
            {serviceType}
          </Chip>
        )}
      </div>

      {description && (
        <Typography className="text-[12px] leading-[1.7]" color="muted" type="body-sm">
          {description}
        </Typography>
      )}

      <div className="mt-auto flex items-center justify-between gap-[12px] border-t border-[var(--separator)] pt-[14px]">
        <Typography type="body-sm">
          {ot("plansPublishedCount", { count: planCount })}
        </Typography>
        <NextLink href={href}>
          <Button size="sm" variant="secondary">
            {ot("viewCompany")}
          </Button>
        </NextLink>
      </div>
    </Card>
  );
}
