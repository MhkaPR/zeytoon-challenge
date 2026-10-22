"use client";

import { Badge, Body } from "@/src/components/ui";
import type { StepProgress as StepProgressItem } from "@/src/lib/api/companies";
import { strings } from "@/src/lib/i18n/strings";

const STEP_LABELS: Record<string, string> = {
  company_information: strings.stepCompanyInfo,
  verification: strings.stepVerification,
};

function stateLabel(state: string, completed: boolean): string {
  if (completed) return strings.stepDone;
  if (state === "locked") return strings.stepLocked;
  return strings.stepPending;
}

/** Shows which registration steps are done and which is pending (FR-026). */
export function StepProgress({
  steps,
  currentStep,
}: {
  steps: StepProgressItem[];
  currentStep?: string | null;
}) {
  return (
    <ol className="flex flex-col gap-[8px]">
      {steps.map((step) => (
        <li
          key={step.step_key}
          aria-current={step.step_key === currentStep ? "step" : undefined}
          className="flex items-center justify-between gap-[8px]"
        >
          <Body>{STEP_LABELS[step.step_key] ?? step.step_key}</Body>
          <Badge>{stateLabel(step.state, step.completed)}</Badge>
        </li>
      ))}
    </ol>
  );
}
