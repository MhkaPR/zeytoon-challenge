"use client";

import { useTranslations } from "next-intl";
import { Check, Clock, Lock, X } from "lucide-react";

import type { StepProgress as StepProgressItem } from "@/src/lib/api/companies";

type StepState = {
  label: string;
  tone: string;
  icon: React.ReactNode;
  ring: string;
};

function resolveState(state: string, completed: boolean, labels: Record<string, string>): StepState {
  if (completed) {
    return {
      label: labels.done,
      tone: "bg-success-soft text-success-soft-foreground",
      icon: <Check className="size-4" />,
      ring: "ring-success/30",
    };
  }
  if (state === "locked") {
    return {
      label: labels.locked,
      tone: "bg-default text-muted",
      icon: <Lock className="size-4" />,
      ring: "ring-border",
    };
  }
  else if ( state === "rejected") {
    return {
      label: labels.rejected,
      tone: "bg-danger text-white",
      icon: <X className="size-4"/>,
      ring: "ring-border",
    }
  }
  return {
    label: labels.pending,
    tone: "bg-warning-soft text-warning-soft-foreground",
    icon: <Clock className="size-4" />,
    ring: "ring-warning/30",
  };
}

/**
 * Vertical stepper showing which registration steps are done, pending, or locked (FR-026).
 * The current step is highlighted and marked as the next action to take.
 */
export function StepProgress({
  steps,
  currentStep,
}: {
  steps: StepProgressItem[];
  currentStep?: string | null;
}) {
  const ot = useTranslations();
  const labels = {
    done: ot("stepDone"), locked: ot("stepLocked"), rejected: ot("stepRejected"), pending: ot("stepPending"),
  };
  const stepLabels: Record<string, string> = { company_information: ot("stepCompanyInfo"), verification: ot("stepVerification") };
  const stepDescriptions: Record<string, string> = { company_information: ot("registerStepInfoDesc"), verification: ot("registerStepVerificationDesc") };
  return (
    <ol className="flex flex-col">
      {steps.map((step, index) => {
        const resolved = resolveState(step.state, step.completed, labels);
        const isCurrent = step.step_key === currentStep;
        const last = index === steps.length - 1;
        return (
          <li key={step.step_key} className="flex gap-[16px]" aria-current={isCurrent ? "step" : undefined}>
            <div className="flex flex-col items-center">
              <span
                aria-hidden
                className={`flex size-[36px] shrink-0 items-center justify-center rounded-full ring-1 ${resolved.tone} ${resolved.ring}`}
              >
                {resolved.icon}
              </span>
              {!last && <span aria-hidden className="my-[4px] w-px flex-1 bg-border" />}
            </div>
            <div className={`flex flex-1 flex-col gap-[4px] ${last ? "pb-0" : "pb-[20px]"}`}>
              <div className="flex flex-wrap items-center gap-[8px]">
                <span className="text-[15px] font-semibold">
                  {stepLabels[step.step_key] ?? step.step_key}
                </span>
                <span
                  className={`rounded-full px-[8px] py-[2px] text-[12px] font-medium ${resolved.tone}`}
                >
                  {resolved.label}
                </span>
                {isCurrent && (
                  <span className="rounded-full bg-accent-soft px-[8px] py-[2px] text-[12px] font-medium text-accent-soft-foreground">
                    {ot("currentStepTitle")}
                  </span>
                )}
              </div>
              {stepDescriptions[step.step_key] && (
                <span className="text-[13px] leading-[1.8] text-muted">
                  {stepDescriptions[step.step_key]}
                </span>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
