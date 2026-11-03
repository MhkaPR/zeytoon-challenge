"use client";

import { useTranslations } from "next-intl";
import { Alert } from "@heroui/react";
import { useEffect, useState } from "react";

import { getPlanEligibility, type PlanEligibility } from "@/src/lib/api/companies";
import { getAccessToken } from "@/src/lib/session";

/**
 * Shows the plan-eligibility gate result for a verified company and names every missing
 * prerequisite so the UI can block the action with the right message (FR-031).
 */
export function PlanEligibilityNotice({ companyId }: { companyId: number }) {
  const ot = useTranslations();
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
          <Alert.Description>{ot("plansGateAllowed")}</Alert.Description>
        </Alert.Content>
      </Alert>
    );
  }
  return (
    <Alert status="warning">
      <Alert.Indicator />
      <Alert.Content>
        <Alert.Description>{ot("panelBlockedVerified")}</Alert.Description>
      </Alert.Content>
    </Alert>
  );
}
