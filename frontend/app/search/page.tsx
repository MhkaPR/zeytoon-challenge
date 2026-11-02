import { Card, Typography } from "@heroui/react";
import { SearchBox } from "@/src/features/home/SearchBox";
import { displayField, getPublishedPlans, planName } from "@/src/lib/api/publicCatalog";
import { strings } from "@/src/lib/i18n/strings";

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await searchParams;
  const raw = params.q;
  const query = Array.isArray(raw) ? (raw[0] ?? "") : (raw ?? "");
  const plans = await getPublishedPlans(query ? { q: query } : {});

  return (
    <main className="mx-auto flex w-full max-w-[960px] flex-1 flex-col gap-[24px] px-[32px] py-[64px]">
      <Typography className="text-[32px] font-semibold" type="h1">{strings.searchTitle}</Typography>
      <SearchBox />
      {query && <Typography color="muted">نتایج جست‌وجو برای «{query}»</Typography>}
      {plans.length ? <div className="grid gap-[14px] sm:grid-cols-2">
        {plans.map((plan) => <Card className="flex flex-col gap-[12px] p-[18px]" key={plan.id}>
          <div><Typography className="font-semibold" type="h2">{planName(plan)}</Typography><a className="text-[12px] text-accent" href={`/companies/${encodeURIComponent(plan.domain)}`}>{plan.company_name} · {plan.domain}</a></div>
          <dl className="grid grid-cols-2 gap-x-[12px] gap-y-[7px] text-[12px]">{Object.entries(plan.values).filter(([, value]) => value != null && value !== "").map(([key, value]) => <div className="contents" key={key}><dt className="text-muted">{displayField(key)}</dt><dd className="text-end">{String(value)}</dd></div>)}</dl>
        </Card>)}
      </div> : <Card variant="secondary"><Card.Header><Card.Title>{query ? "طرحی پیدا نشد" : strings.resultsEmptyTitle}</Card.Title><Card.Description>{query ? "عبارت دیگری جست‌وجو کنید." : "برای دیدن طرح‌های منتشرشده جست‌وجو کنید."}</Card.Description></Card.Header></Card>}
    </main>
  );
}
