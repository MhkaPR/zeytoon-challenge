import { useTranslations } from "next-intl";
import { Card, Typography } from "@heroui/react";

/** Persian digits, so criterion markers read as ۱، ۲، ۳ … (DESIGN.md §8). */
const ORDINALS = ["۱", "۲", "۳", "۴", "۵"] as const;

/** Transparent explanation of the criteria used to rank companies and hosts (homepage). */
export function RankingCriteria() {
  const ot = useTranslations();
  const rankingCriteria = ot.raw("rankingCriteria") as Array<{ title: string; body: string }>;
  return (
    <section className="flex flex-col gap-[24px]">
      <div className="flex flex-col gap-[8px]">
        <Typography className="text-[28px] font-semibold" type="h2">
          {ot("rankingTitle")}
        </Typography>
        <Typography className="max-w-[720px] leading-[1.8]" color="muted">
          {ot("rankingIntro")}
        </Typography>
      </div>

      <div className="grid grid-cols-1 gap-[16px] sm:grid-cols-2 lg:grid-cols-3">
        {rankingCriteria.map((criterion, index) => (
          <Card key={criterion.title} className="flex flex-col gap-[8px] p-[24px]">
            <div className="flex flex-row items-center justify-between gap-[8px]">
              <Card.Title>{criterion.title}</Card.Title>
              <span aria-hidden className="font-mono text-[12px] font-medium text-muted">
                {ORDINALS[index]}
              </span>
            </div>
            <Card.Description>{criterion.body}</Card.Description>
          </Card>
        ))}
      </div>
    </section>
  );
}
