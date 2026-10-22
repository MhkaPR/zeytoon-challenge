import { Header } from "@/src/features/site/Header";
import { Body, Card, DisplayHero } from "@/src/components/ui";
import { strings } from "@/src/lib/i18n/strings";

/** About page placeholder for the header's "about us" menu item. */
export default function AboutPage() {
  return (
    <>
      <Header />
      <main className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-[32px] px-[32px] py-[80px]">
        <DisplayHero className="text-[40px]">{strings.navAboutUs}</DisplayHero>
        <Card variant="plain">
          <Body tone="muted">{strings.heroSubtitle}</Body>
        </Card>
      </main>
    </>
  );
}
