"use client";

import { Skeleton, Typography } from "@heroui/react";
import { useRouter } from "next/navigation";
import { use } from "react";

import { ContinueRegistration } from "@/src/features/company/ContinueRegistration";
import { CompanyOverview } from "@/src/features/panel/CompanyOverview";
import { CompanySwitcher } from "@/src/features/panel/CompanySwitcher";
import { useActiveCompany } from "@/src/features/panel/useActiveCompany";
import { strings } from "@/src/lib/i18n/strings";

/**
 * Panel route for a selected company. The backend resolves full-panel vs continue view and
 * never renders the full panel for an unverified company (FR-024, FR-025, FR-027).
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
  const companies = switcher?.companies ?? [];

  return (
    <main className="mx-auto flex w-full max-w-[1000px] flex-1 flex-col gap-[28px] px-[16px] py-[40px] sm:px-[24px] md:px-[32px] md:py-[64px]">
      <Typography className="text-[26px] font-semibold sm:text-[32px]" type="h1">
        {strings.companyPanel}
      </Typography>

      {loading ? (
        <div className="flex flex-col gap-[16px]">
          <Skeleton className="h-[110px] rounded-[var(--radius)]" />
          <Skeleton className="h-[240px] rounded-[var(--radius)]" />
        </div>
      ) : (
        <>
          {companies.length > 1 && <CompanySwitcher activeId={id} companies={companies} />}
          {entry?.view === "continue_registration" ? (
            <ContinueRegistration 
              company={entry.company}
              currentStep={entry.current_step}
              onContinue={(companyId) => router.push(`/panel/${companyId}`)}
              steps={entry.step_progress}
            />
          ) : entry?.view === "full_panel" ? (
            <CompanyOverview company={entry.company} />
          ) : null}
        </>
      )}
    </main>
  );
}
