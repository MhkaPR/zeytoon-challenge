import { Card, Typography } from "@heroui/react";

import { Header } from "@/src/features/site/Header";
import { strings } from "@/src/lib/i18n/strings";

/** Provider directory placeholder; results are owned by the search/comparison feature. */
export default function CompaniesPage() {
  return (
    <>
      <Header />
      <main className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-[32px] px-[32px] py-[80px]">
        <Typography className="text-[40px] font-semibold" type="h1">
          {strings.navCompanies}
        </Typography>
        <Card>
          <Typography color="muted">{strings.resultsPending}</Typography>
        </Card>
      </main>
    </>
  );
}
