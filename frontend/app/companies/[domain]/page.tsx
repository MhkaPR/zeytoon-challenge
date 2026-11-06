import { Typography } from "@heroui/react";
import { getTranslations } from "next-intl/server";

import { PlanCatalog } from "@/src/features/home/PlanCatalog";
import { getPlansPage } from "@/src/lib/api/publicCatalog";

type Props = { params: Promise<{ domain: string }> };

/** Company comparison, rendered on the server from the public catalog API. */
export default async function CompanyPublicPage({ params }: Props) {
  const { domain } = await params;
  const decodedDomain = decodeURIComponent(domain);
  const [ot, plansPage] = await Promise.all([
    getTranslations(),
    getPlansPage({ domain: decodedDomain, page_size: "12" }),
  ]);
  const companyName = plansPage.plans[0]?.company_name ?? decodedDomain;

  return (
    <main className="mx-auto flex w-full max-w-[1100px] flex-1 flex-col gap-[24px] px-[24px] py-[56px] sm:px-[32px]">
      <div>
        <Typography className="text-[34px] font-semibold" type="h1">{companyName}</Typography>
        <Typography color="muted">{decodedDomain}</Typography>
      </div>
      <PlanCatalog
        ariaLabel={ot("publishedPlansTitle")}
        baseParams={{ domain: decodedDomain }}
        description={null}
        emptyState={
          <div className="rounded-[var(--radius)] bg-surface-secondary p-[24px]">
            <Typography color="muted">{ot("companyNoPlans")}</Typography>
          </div>
        }
        headerAction={null}
        plansPage={plansPage}
        showServiceTabs={false}
        title={ot("publishedPlansTitle")}
      />
    </main>
  );
}
