import { Card, Typography } from "@heroui/react";

import { howItWorksSteps, strings } from "@/src/lib/i18n/strings";

/**
 * Step-by-step guide to using the site. Three numbered steps form the olive tonal ramp from
 * DESIGN.md §4 (Develop → Preview → Ship), each step carrying its own olive tone.
 */
export function HowItWorks() {
  return (
    <section className="flex flex-col gap-[24px]">
      <div className="flex flex-col gap-[8px]">
        <Typography className="text-[28px] font-semibold" type="h2">
          {strings.howItWorksTitle}
        </Typography>
        <Typography className="max-w-[720px] leading-[1.8]" color="muted">
          {strings.howItWorksIntro}
        </Typography>
      </div>

      <ol className="grid grid-cols-1 gap-[16px] md:grid-cols-3">
        {howItWorksSteps.map((step) => (
          <li key={step.index}>
            <Card className="flex h-full flex-col gap-[8px] p-[24px]" variant="secondary">
              <div className="flex flex-row items-center gap-[8px]">
                <span
                  aria-hidden
                  className="flex size-[28px] shrink-0 items-center justify-center rounded-full font-mono text-[13px] font-medium text-accent-foreground"
                  style={{ background: step.tone }}
                >
                  {step.index}
                </span>
                <Typography className="font-mono text-[12px] uppercase" color="muted" type="body-xs">
                  {step.label}
                </Typography>
              </div>
              <Card.Title>{step.title}</Card.Title>
              <Card.Description>{step.body}</Card.Description>
            </Card>
          </li>
        ))}
      </ol>
    </section>
  );
}
