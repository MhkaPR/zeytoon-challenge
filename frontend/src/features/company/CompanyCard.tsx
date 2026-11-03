import { useTranslations } from "next-intl";
import { Card, Chip, Typography } from "@heroui/react";
import NextLink from "next/link";

/**
 * ``company_card`` (PAGES.yaml): a vertical card whose block is the company explained.
 * Used on listing/search surfaces to summarize a provider.
 */
export function CompanyCard({
  name,
  domain,
  description,
  serviceType,
}: {
  name: string;
  domain?: string;
  description?: string;
  serviceType?: string;
}) {
  const ot = useTranslations();
  return (
    <NextLink
      aria-label={name}
      className="block h-full rounded-[var(--radius)] focus-visible:outline-none"
      href={domain ? `/companies/${encodeURIComponent(domain)}` : "/companies"}
    >
      <Card
        className="flex h-full flex-col gap-[8px] p-[24px] transition-shadow hover:shadow-overlay"
        variant="tertiary"
      >
        <div className="flex flex-row items-start justify-between gap-[8px]">
          <Card.Title>{name}</Card.Title>
          {serviceType && (
            <Chip color="accent" size="sm" variant="soft">
              {serviceType}
            </Chip>
          )}
        </div>
        {domain && (
          <Typography className="text-[12px]" type="code">
            {domain}
          </Typography>
        )}
        <Card.Description>{description || ot("companyCardFallback")}</Card.Description>
      </Card>
    </NextLink>
  );
}
