"use client";

import { Body, Button, Card, CardTitle } from "@/src/components/ui";
import type { Company, StepProgress as StepProgressItem } from "@/src/lib/api/companies";
import { strings } from "@/src/lib/i18n/strings";

import { StepProgress } from "./StepProgress";

function outcomeLabel(status: Company["verification_status"]): string {
  if (status === "rejected") return strings.rejectedStatus;
  return strings.pendingStatus;
}

/**
 * Shown instead of the full panel for a pending or rejected company (FR-025). It
 * communicates the current outcome (pending / not approved) but never the recorded reason
 * (FR-021), and offers the route to the current step (FR-026).
 */
export function ContinueRegistration({
  company,
  steps,
  currentStep,
  onContinue,
}: {
  company: Company;
  steps: StepProgressItem[];
  currentStep?: string | null;
  onContinue?: (companyId: number) => void;
}) {
  return (
    <Card variant="featured" className="flex flex-col gap-[16px] p-[32px]">
      <CardTitle>{strings.continueRegistration}</CardTitle>
      <Body className="text-[var(--ds-text-muted)]">
        {company.company_name} — {outcomeLabel(company.verification_status)}
      </Body>
      <StepProgress steps={steps} currentStep={currentStep} />
      <Button variant="primary" onClick={() => onContinue?.(company.id)}>
        {strings.goToCurrentStep}
      </Button>
    </Card>
  );
}
