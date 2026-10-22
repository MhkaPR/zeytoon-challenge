import Link from "next/link";

import { Badge, Body, Card, CardTitle, MonoLabel } from "@/src/components/ui";
import { strings } from "@/src/lib/i18n/strings";

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
  return (
    <Link href={domain ? `/companies/${encodeURIComponent(domain)}` : "/companies"}>
      <Card variant="featured" className="flex h-full flex-col gap-[8px] p-[24px]">
        <CardTitle>{name}</CardTitle>
        {domain && <MonoLabel>{domain}</MonoLabel>}
        {serviceType && <Badge>{serviceType}</Badge>}
        <Body tone="muted">{description || strings.companyCardFallback}</Body>
      </Card>
    </Link>
  );
}
