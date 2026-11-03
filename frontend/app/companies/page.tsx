import { getTranslations } from "next-intl/server";
import { Card, Typography } from "@heroui/react";
import Link from "next/link";

import { getPublishedPlans, planName } from "@/src/lib/api/publicCatalog";
export default async function CompaniesPage() {
  const ot = await getTranslations();
  const plans = await getPublishedPlans();
  const providers = [...new Map(plans.map((plan) => [plan.domain, plan])).values()];
  return (
    <main className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-[32px] px-[32px] py-[64px]">
      <div><Typography className="text-[40px] font-semibold" type="h1">{ot("navCompanies")}</Typography><Typography color="muted">{ot("companiesIntro")}</Typography></div>
      {providers.length ? <div className="grid gap-[16px] sm:grid-cols-2 lg:grid-cols-3">
        {providers.map((provider) => {
          const providerPlans = plans.filter((plan) => plan.domain === provider.domain);
          return <Link href={`/companies/${encodeURIComponent(provider.domain)}`} key={provider.domain}>
            <Card className="flex h-full flex-col gap-[10px] p-[20px]"><Typography className="font-semibold" type="h2">{provider.company_name}</Typography><Typography color="muted" type="body-sm">{provider.domain}</Typography><Typography type="body-sm">{ot("plansPublishedCount", { count: providerPlans.length })}</Typography><Typography color="muted" type="body-xs">{planName(providerPlans[0])}</Typography></Card>
          </Link>;
        })}
      </div> : <Card className="p-[24px]" variant="secondary"><Typography color="muted">{ot("companiesEmpty")}</Typography></Card>}
    </main>
  );
}
