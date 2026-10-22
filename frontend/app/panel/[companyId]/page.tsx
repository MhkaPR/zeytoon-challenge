"use client";

import { Card, Typography } from "@heroui/react";
import { useRouter } from "next/navigation";
import { use } from "react";

import { ContinueRegistration } from "@/src/features/company/ContinueRegistration";
import { CompanySwitcher } from "@/src/features/panel/CompanySwitcher";
import { PlanEligibilityNotice } from "@/src/features/panel/PlanEligibilityNotice";
import { useActiveCompany } from "@/src/features/panel/useActiveCompany";
import { strings } from "@/src/lib/i18n/strings";

/**
 * Panel route for a selected company. The backend resolves full-panel vs continue view and
 * redirects unverified companies away from the full panel, so a direct URL never renders the
 * full panel for an unverified company (FR-024, FR-025, FR-027).
 */
export default function CompanyPanelPage({
  params,
}: {
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = use(params);
  const router = useRouter();
  const id = Number(companyId);
  const { switcher, entry, loading } = useActiveCompany(id);

  return (
    <main className="mx-auto flex w-full max-w-[1000px] flex-1 flex-col gap-[24px] px-[32px] py-[64px]">
      <Typography className="text-[36px] font-semibold" type="h1">
        {strings.companyPanel}
      </Typography>
      <CompanySwitcher companies={switcher?.companies ?? []} activeId={id} />
      {loading ? null : entry?.view === "continue_registration" ? (
        <ContinueRegistration
          company={entry.company}
          steps={entry.step_progress}
          currentStep={entry.current_step}
          onContinue={(companyId) => router.push(`/panel/${companyId}`)}
        />
      ) : entry?.view === "full_panel" ? (
        <Card className="flex flex-col gap-[8px] p-[32px]" variant="tertiary">
          <Card.Title>{strings.fullPanel}</Card.Title>
          <Typography>{entry.company.company_name}</Typography>
          <PlanEligibilityNotice companyId={entry.company.id} />
        </Card>
      ) : null}
    </main>
  );
}
