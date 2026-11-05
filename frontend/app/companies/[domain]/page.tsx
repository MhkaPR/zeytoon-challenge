import { Card, Typography } from "@heroui/react";
import { getTranslations } from "next-intl/server";

import { PlanCard } from "@/src/features/home/planCatalog/PlanCard";
import { getPublishedPlans } from "@/src/lib/api/publicCatalog";

type Props = { params: Promise<{ domain: string }> };

/** Company comparison, rendered on the server from the public catalog API. */
export default async function CompanyPublicPage({ params }: Props) {
  const { domain } = await params;
  const decodedDomain = decodeURIComponent(domain);
  const [ot, plans] = await Promise.all([
    getTranslations(),
    getPublishedPlans({ domain: decodedDomain }),
  ]);
  const companyName = plans[0]?.company_name ?? decodedDomain;

  return (
    <main className="mx-auto flex w-full max-w-[1100px] flex-1 flex-col gap-[24px] px-[24px] py-[56px] sm:px-[32px]">
      <div>
        <Typography className="text-[34px] font-semibold" type="h1">{companyName}</Typography>
        <Typography color="muted">{decodedDomain}</Typography>
      </div>
      <Typography className="text-[22px] font-semibold" type="h2">{ot("publishedPlansTitle")}</Typography>
      {plans.length ? (
        <div className="grid gap-[14px] sm:grid-cols-2 lg:grid-cols-3">
          {plans.map((plan) => <PlanCard key={plan.id} plan={plan} />)}
        </div>
      ) : (
        <Card className="p-[24px]" variant="secondary">
          <Typography color="muted">{ot("companyNoPlans")}</Typography>
        </Card>
      )}
    </main>
  );
}
