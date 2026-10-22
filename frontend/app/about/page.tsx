import { Card, Typography } from "@heroui/react";

import { Header } from "@/src/features/site/Header";
import { strings } from "@/src/lib/i18n/strings";

/** About page placeholder for the header's "about us" menu item. */
export default function AboutPage() {
  return (
    <>
      <Header />
      <main className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-[32px] px-[32px] py-[80px]">
        <Typography className="text-[40px] font-semibold" type="h1">
          {strings.navAboutUs}
        </Typography>
        <Card>
          <Typography color="muted">{strings.heroSubtitle}</Typography>
        </Card>
      </main>
    </>
  );
}
