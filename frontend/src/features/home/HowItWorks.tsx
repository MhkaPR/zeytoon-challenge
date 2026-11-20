import { useTranslations } from "next-intl";
import { Button, Card, Typography } from "@/src/features/ui/heroUi";

import { ChevronLeft, ChevronDown} from "lucide-react";
/**
 * Step-by-step guide to using the site. Three numbered steps form the olive tonal ramp from
 * DESIGN.md §4 (Develop → Preview → Ship), each step carrying its own olive tone.
 */
export function HowItWorks() {
  const ot = useTranslations();
  const howItWorksSteps = ot.raw("howItWorksSteps") as Array<{ index: string; label: string; title: string; body: string; tone: string }>;
  return (
    <section className="flex flex-col gap-[24px]">
      <div className="flex flex-col gap-[8px]">
        <Typography className="text-[28px] font-semibold" type="h2">
          {ot("howItWorksTitle")}
        </Typography>
        <Typography className="max-w-[720px] leading-[1.8]" color="muted">
          {ot("howItWorksIntro")}
        </Typography>
      </div>

<ol className="grid grid-cols-1 gap-[16px] md:grid-cols-3">
  {howItWorksSteps.map((step, i) => (
    <li key={step.index} className="relative">
      <Card className="flex h-full flex-col gap-[8px] p-[24px]" variant="default">
        <div className="flex flex-row items-center gap-[8px]">
          <span
            aria-hidden
            className="flex size-[28px] shrink-0 items-center justify-center rounded-full text-[13px] font-medium text-accent-foreground"
            style={{ background: step.tone }}
          >
            {step.index}
          </span>
          <Typography className="text-[12px] uppercase" color="muted" type="body-xs">
            {step.label}
          </Typography>
        </div>
        <Card.Title>{step.title}</Card.Title>
        <Card.Description>{step.body}</Card.Description>
      </Card>

      {i < howItWorksSteps.length - 1 && (
        <span
          aria-hidden
          className="pointer-events-none absolute top-1/2 hidden size-[24px] -translate-y-1/2 items-center justify-center md:flex"
          style={{
            insetInlineEnd: "calc(-1 * (16px / 2) - 12px)", // -(gap/2 + size/2)
          }}
        >
          <ChevronLeft className="size-[18px]" />
        </span>
      )}
    </li>
  ))}
</ol>
    </section>
  );
}
