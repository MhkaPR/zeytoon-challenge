import { getTranslations } from "next-intl/server";

import { Card, Typography } from "@/src/features/ui/heroUi";

/** About page placeholder for the header's "about us" menu item. */
export default async function AboutPage() {
  const ot = await getTranslations();
  return (
    <main className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-[32px] px-[32px] py-[80px]">
      <Typography className="text-[40px] font-semibold" type="h1">
        {ot("navAboutUs")}
      </Typography>
      <Card>
        <Typography color="muted">{ot("heroSubtitle")}</Typography>
      </Card>
    </main>
  );
}
