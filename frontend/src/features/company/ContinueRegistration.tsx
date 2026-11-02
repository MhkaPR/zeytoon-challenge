"use client";

import { useTranslations } from "next-intl";
import { AlertDialog, Button, Card, Chip, Typography } from "@heroui/react";
import { AlertCircle, ArrowLeft, Globe } from "lucide-react";

import type { Company, StepProgress as StepProgressItem } from "@/src/lib/api/companies";
import { verificationColor, verificationLabel } from "@/src/features/panel/status";
import { strings } from "@/src/lib/i18n/strings";
import { StepProgress } from "./StepProgress";

function statusHint(status: Company["verification_status"]): string {
  if (status === "rejected") return strings.rejectedHint;
  return strings.pendingHint;
}

/**
 * Shown instead of the full panel for a pending or rejected company (FR-025). It states the
 * current outcome (pending / not approved) without ever revealing the recorded reason
 * (FR-021), shows the registration steps, and routes the owner to the current step (FR-026).
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
  const t = useTranslations("common");
  return (
    <div className="flex flex-col gap-[24px]">
      <Card className="p-6">
        {/* Title row: the company name and its status, with the status-explainer trigger
            sitting directly next to the title. */}
        <div className="flex flex-wrap items-start justify-between gap-[16px]">
          <div className="flex items-center gap-[10px]">
            <div className="flex flex-col gap-[6px]">
              <Typography className="text-[20px] font-semibold" type="h2">
                {company.company_name}
              </Typography>
              <span className="flex items-center gap-[6px] text-[13px] text-muted" dir="ltr">
                <Globe className="size-4 shrink-0" />
                {company.domain}
              </span>
            </div>
          </div>

          <Chip color={verificationColor(company.verification_status)} variant="primary">
            {verificationLabel(company.verification_status)}
          </Chip>
        </div>

        <div className="mt-4 flex flex-col gap-4">
          <div className="flex flex-col gap-[4px]">
            <Typography className="text-[18px] font-semibold" type="h2">
              {t("registerCompanyStepsTitle")}
            </Typography>
            <Typography className="text-[13px] leading-[1.8]" color="muted">
              {t("nextStepHint")}
            </Typography>
          </div>
          <StepProgress currentStep={currentStep} steps={steps} />
          <Button
            className="w-full sm:w-auto sm:self-start"
            onPress={() => onContinue?.(company.id)}
          >
            <ArrowLeft aria-hidden className="size-4" />
            {t("goToCurrentStep")}
          </Button>
        </div>
      </Card>
    </div>
  );
}
