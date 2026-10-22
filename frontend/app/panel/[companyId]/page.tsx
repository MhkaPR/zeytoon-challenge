"use client";

import { useRouter } from "next/navigation";
import { use } from "react";

import { Body, Card, CardTitle, DisplayHero } from "@/src/components/ui";
import { PlanEligibilityNotice } from "@/src/features/panel/PlanEligibilityNotice";
import { ContinueRegistration } from "@/src/features/company/ContinueRegistration";
import { CompanySwitcher } from "@/src/features/panel/CompanySwitcher";
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
      <DisplayHero className="text-[36px]">{strings.companyPanel}</DisplayHero>
      <CompanySwitcher companies={switcher?.companies ?? []} activeId={id} />
      {loading ? null : entry?.view === "continue_registration" ? (
        <ContinueRegistration
          company={entry.company}
          steps={entry.step_progress}
          currentStep={entry.current_step}
          onContinue={(companyId) => router.push(`/panel/${companyId}`)}
        />
      ) : entry?.view === "full_panel" ? (
        <Card variant="featured" className="flex flex-col gap-[8px] p-[32px]">
          <CardTitle>{strings.fullPanel}</CardTitle>
          <Body>{entry.company.company_name}</Body>
          <PlanEligibilityNotice companyId={entry.company.id} />
        </Card>
      ) : null}
    </main>
  );
}
