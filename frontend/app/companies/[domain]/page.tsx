import { Card, Typography } from "@heroui/react";
import type { Metadata } from "next";

import { displayField, getPublishedPlans, planName } from "@/src/lib/api/publicCatalog";

type Props = { params: Promise<{ domain: string }> };

// Company domains are runtime data and the page must render on the server per request.
export const instant = false;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { domain } = await params;
  const decoded = decodeURIComponent(domain);
  const plans = await getPublishedPlans({ domain: decoded });
  return {
    title: plans[0]?.company_name ?? decoded,
    description: plans.length
      ? `Compare ${plans.length} published plans from ${plans[0].company_name}.`
      : `Published service plans from ${decoded}.`,
  };
}

export default async function CompanyPublicPage({ params }: Props) {
  const { domain } = await params;
  const decoded = decodeURIComponent(domain);
  const plans = await getPublishedPlans({ domain: decoded });
  const companyName = plans[0]?.company_name ?? decoded;
  return (
    <main className="mx-auto flex w-full max-w-[1100px] flex-1 flex-col gap-[24px] px-[24px] py-[56px] sm:px-[32px]">
      <div><Typography className="text-[34px] font-semibold" type="h1">{companyName}</Typography><Typography color="muted">{decoded}</Typography></div>
      <Typography className="text-[22px] font-semibold" type="h2">طرح‌های منتشرشده</Typography>
      {plans.length ? <div className="grid gap-[14px] sm:grid-cols-2 lg:grid-cols-3">{plans.map((plan) => <Card className="flex flex-col gap-[12px] p-[18px]" key={plan.id}>
        <Typography className="font-semibold" type="h2">{planName(plan)}</Typography>
        <Typography color="muted" type="body-sm">{plan.plan_type}</Typography>
        <dl className="grid grid-cols-2 gap-x-[12px] gap-y-[7px] text-[12px]">{Object.entries(plan.values).filter(([, value]) => value != null && value !== "").map(([key, value]) => <div className="contents" key={key}><dt className="text-muted">{displayField(key)}</dt><dd className="text-end">{String(value)}</dd></div>)}</dl>
      </Card>)}</div> : <Card variant="secondary" className="p-[24px]"><Typography color="muted">در حال حاضر طرح منتشرشده‌ای برای این ارائه‌دهنده ثبت نشده است.</Typography></Card>}
    </main>
  );
}
