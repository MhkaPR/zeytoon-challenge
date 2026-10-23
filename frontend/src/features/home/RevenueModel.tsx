import { Card, Typography } from "@heroui/react";

import { revenueItems, strings } from "@/src/lib/i18n/strings";

/**
 * Plain explanation of how the platform makes money. States outright that featured
 * placement never changes the ranking criteria, so the model stays transparent.
 */
export function RevenueModel() {
  return (
    <section className="flex flex-col gap-[24px]">
      <div className="flex flex-col gap-[8px]">
        <Typography className="text-[28px] font-semibold" type="h2">
          {strings.revenueTitle}
        </Typography>
        <Typography className="max-w-[720px] leading-[1.8]" color="muted">
          {strings.revenueIntro}
        </Typography>
      </div>

      <div className="grid grid-cols-1 gap-[16px] sm:grid-cols-3">
        {revenueItems.map((item) => (
          <Card key={item.title} className="flex flex-col gap-[8px] p-[24px]" variant="secondary">
            <Card.Title>{item.title}</Card.Title>
            <Card.Description>{item.body}</Card.Description>
          </Card>
        ))}
      </div>

      <Typography className="text-[14px]" color="muted" type="body-sm">
        {strings.revenueNote}
      </Typography>
    </section>
  );
}
