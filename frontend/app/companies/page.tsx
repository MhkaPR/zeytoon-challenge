import { Header } from "@/src/features/site/Header";
import { Card, DisplayHero, Body } from "@/src/components/ui";
import { strings } from "@/src/lib/i18n/strings";

/** Provider directory placeholder; results are owned by the search/comparison feature. */
export default function CompaniesPage() {
  return (
    <>
      <Header />
      <main className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-[32px] px-[32px] py-[80px]">
        <DisplayHero className="text-[40px]">{strings.navCompanies}</DisplayHero>
        <Card variant="plain">
          <Body tone="muted">{strings.resultsPending}</Body>
        </Card>
      </main>
    </>
  );
}
