import {Card, Surface, Typography} from "@heroui/react";

import { strings } from "@/src/lib/i18n/strings";

const POINTS = [
  { title: strings.aboutTorbPoint1Title, body: strings.aboutTorbPoint1Body },
  { title: strings.aboutTorbPoint2Title, body: strings.aboutTorbPoint2Body },
  { title: strings.aboutTorbPoint3Title, body: strings.aboutTorbPoint3Body },
  { title: strings.aboutTorbPoint4Title, body: strings.aboutTorbPoint4Body },
] as const;

/** Short introduction explaining what Torb Host is and why it is useful (homepage). */
export function AboutTorb() {
  return (
    <section className="flex sm:flex-row flex-col gap-[24px]">
      <div className="flex flex-col gap-[8px]">
        <Typography className="text-[28px] font-semibold" type="h2">
          {strings.aboutTorbTitle}
        </Typography>
        <Typography className="max-w-[720px] leading-[1.8]" color="muted">
          {strings.aboutTorbBody}
        </Typography>
      </div>

      <div className="grid gap-[16px] grid-cols-2">
        {POINTS.map((point) => (
          <Card key={point.title} className="flex flex-col gap-[8px] p-[24px]" variant="default">
            <Card.Title>{point.title}</Card.Title>
            <Card.Description>{point.body}</Card.Description>
          </Card>
        ))}
      </div>
    </section>
  );
}
