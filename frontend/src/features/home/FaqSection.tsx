import { useTranslations } from "next-intl";
import { Accordion, Typography } from "@heroui/react";

import { faqItems } from "@/src/lib/i18n/strings";
/**
 * Frequently asked questions as a single-expandable HeroUI ``Accordion`` (homepage FAQ).
 * The built-in indicator chevron is used, so no icon library is required.
 */
export function FaqSection() {
  const t = useTranslations("common");
  return (
    <section className="flex flex-col gap-[24px]">
      <div className="flex flex-col gap-[8px]">
        <Typography className="text-[28px] font-semibold" type="h2">
          {t("faqTitle")}
        </Typography>
        <Typography className="max-w-[720px] leading-[1.8]" color="muted">
          {t("faqIntro")}
        </Typography>
      </div>

      <Accordion className="w-full" variant="surface">
        {faqItems.map((item) => (
          <Accordion.Item key={item.question}>
            <Accordion.Heading>
              <Accordion.Trigger>
                {item.question}
                <Accordion.Indicator />
              </Accordion.Trigger>
            </Accordion.Heading>
            <Accordion.Panel>
              <Accordion.Body>{item.answer}</Accordion.Body>
            </Accordion.Panel>
          </Accordion.Item>
        ))}
      </Accordion>
    </section>
  );
}
