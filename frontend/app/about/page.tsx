import { useTranslations } from "next-intl";
import { Card, Typography } from "@heroui/react";

/** About page placeholder for the header's "about us" menu item. */
export default function AboutPage() {
  const ot = useTranslations();
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
