"use client";

import { Button, Card, Chip, Typography } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { strings } from "@/src/lib/i18n/strings";

import { CompanyForm } from "./CompanyForm";

/** The two registration steps, shown below the intro so the owner knows what is coming. */
const STEPS = [
  { index: "۱", title: strings.stepCompanyInfo, body: strings.registerStepInfoDesc },
  { index: "۲", title: strings.stepVerification, body: strings.registerStepVerificationDesc },
] as const;

/** Explanatory hints shown before the form so the owner knows what to prepare. */
const HINTS = [
  strings.companyDomain,
  strings.companyName,
  strings.representativeName,
  strings.companyPhone,
] as const;

/**
 * The dedicated company-registration page. It explains what company registration is and how
 * it works, lists the registration steps, and hosts the step-one form. Once a company has been
 * submitted it offers a button to go to the owner's company panel (requirement: registration
 * page with title, description, hints, steps, and a panel button after submission).
 */
export function CompanyRegistrationPage() {
  const router = useRouter();
  const [createdId, setCreatedId] = useState<number | null>(null);

  return (
    <main className="mx-auto flex w-full max-w-[920px] flex-1 flex-col gap-[40px] px-[32px] py-[64px]">
      <header className="flex flex-col gap-[16px]">
        <Typography className="text-[40px] font-semibold" type="h1">
          {strings.registerCompanyTitle}
        </Typography>
        <Typography className="max-w-[680px] leading-[1.9]" color="muted">
          {strings.registerCompanyIntro}
        </Typography>
      </header>

      <Card className="flex flex-col gap-[16px] p-[24px]" variant="secondary">
        <Card.Title>{strings.registerCompanyHintsTitle}</Card.Title>
        <ul className="flex flex-wrap gap-[8px]">
          {HINTS.map((hint) => (
            <li key={hint}>
              <Chip variant="soft">{hint}</Chip>
            </li>
          ))}
        </ul>
      </Card>

      <section className="flex flex-col gap-[16px]">
        <Typography className="text-[24px] font-semibold" type="h2">
          {strings.registerCompanyStepsTitle}
        </Typography>
        <Typography className="leading-[1.8]" color="muted">
          {strings.registerCompanyStepsIntro}
        </Typography>
        <ol className="grid grid-cols-1 gap-[16px] md:grid-cols-2">
          {STEPS.map((step) => (
            <li key={step.index}>
              <Card className="flex h-full flex-col gap-[8px] p-[24px]" variant="default">
                <div className="flex flex-row items-center gap-[8px]">
                  <span
                    aria-hidden
                    className="flex size-[28px] shrink-0 items-center justify-center rounded-full bg-accent text-[13px] font-medium text-accent-foreground"
                  >
                    {step.index}
                  </span>
                  <Card.Title>{step.title}</Card.Title>
                </div>
                <Card.Description>{step.body}</Card.Description>
              </Card>
            </li>
          ))}
        </ol>
      </section>

      {createdId === null ? (
        <CompanyForm onCreated={setCreatedId} />
      ) : (
        <Card className="flex flex-col items-start gap-[16px] p-[32px]" variant="tertiary">
          <Card.Title>{strings.registerCompanyCreatedTitle}</Card.Title>
          <Typography className="leading-[1.8]" color="muted">
            {strings.registerCompanyCreatedBody}
          </Typography>
          <Button onPress={() => router.push("/panel")}>{strings.goToCompaniesPanel}</Button>
        </Card>
      )}
    </main>
  );
}
