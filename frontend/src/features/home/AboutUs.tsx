import { useTranslations } from "next-intl";
import {Card, Typography} from "@heroui/react";


/** Short introduction explaining what Torb Host is and why it is useful (homepage). */
export function AboutUs() {
  const ot = useTranslations();
  const points = [1, 2, 3, 4].map((index) => ({
    title: ot(`aboutTorbPoint${index}Title`),
    body: ot(`aboutTorbPoint${index}Body`),
  }));
  return (
    <section className="flex sm:flex-row flex-col gap-[24px]">
      <div className="flex flex-col gap-[8px]">
        <Typography className="text-[28px] font-semibold" type="h2">
          {ot("aboutTorbTitle")}
        </Typography>
        <Typography className="max-w-[720px] leading-[1.8]" color="muted">
          {ot("aboutTorbBody")}
        </Typography>
      </div>

      <div className="grid gap-[16px] grid-cols-2">
        {points.map((point) => (
          <Card key={point.title} className="flex flex-col gap-[8px] p-[24px]" variant="default">
            <Card.Title>{point.title}</Card.Title>
            <Card.Description>{point.body}</Card.Description>
          </Card>
        ))}
      </div>
    </section>
  );
}
