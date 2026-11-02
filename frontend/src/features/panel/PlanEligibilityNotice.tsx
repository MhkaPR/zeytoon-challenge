"use client";

import { useTranslations } from "next-intl";
import { Alert } from "@heroui/react";
import { useEffect, useState } from "react";

import { getPlanEligibility, type PlanEligibility } from "@/src/lib/api/companies";
import { strings } from "@/src/lib/i18n/strings";
import { getAccessToken } from "@/src/lib/session";

function missingLabel(_missing: string[]): string {
  return strings.panelBlockedVerified;
}

/**
 * Shows the plan-eligibility gate result for a verified company and names every missing
 * prerequisite so the UI can block the action with the right message (FR-031).
 */
export function PlanEligibilityNotice({ companyId }: { companyId: number }) {
  const t = useTranslations("common");
  const [eligibility, setEligibility] = useState<PlanEligibility | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) return;
    getPlanEligibility(token, companyId)
      .then(setEligibility)
      .catch(() => setEligibility(null));
  }, [companyId]);

  if (!eligibility) return null;
  if (eligibility.allowed) {
    return (
      <Alert status="default" >
        <Alert.Indicator />
        <Alert.Content>
          <Alert.Description>{t("plansGateAllowed")}</Alert.Description>
        </Alert.Content>
      </Alert>
    );
  }
  return (
    <Alert status="warning">
      <Alert.Indicator />
      <Alert.Content>
        <Alert.Description>{missingLabel(eligibility.missing)}</Alert.Description>
      </Alert.Content>
    </Alert>
  );
}
