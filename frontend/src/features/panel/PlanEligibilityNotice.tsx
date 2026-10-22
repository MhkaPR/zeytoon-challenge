"use client";

import { Alert, Chip } from "@heroui/react";
import { useEffect, useState } from "react";

import { getPlanEligibility, type PlanEligibility } from "@/src/lib/api/companies";
import { strings } from "@/src/lib/i18n/strings";
import { getAccessToken } from "@/src/lib/session";

function missingLabel(missing: string[]): string {
  if (missing.length > 1) return strings.panelBlockedBoth;
  if (missing.includes("charged")) return strings.panelBlockedCharged;
  return strings.panelBlockedVerified;
}

/**
 * Shows the plan-eligibility gate result for a verified company and names every missing
 * prerequisite so the UI can block the action with the right message (FR-031).
 */
export function PlanEligibilityNotice({ companyId }: { companyId: number }) {
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
    return <Chip color="success">{strings.verifiedStatus}</Chip>;
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
