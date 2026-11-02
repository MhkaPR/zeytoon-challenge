"use client";

import {Button, Chip, Skeleton, Tabs, Typography} from "@heroui/react";
import { useRouter, usePathname } from "next/navigation";
import { use } from "react";
import { Plus } from "lucide-react";
import NextLink from "next/link";

import { ContinueRegistration } from "@/src/features/company/ContinueRegistration";
import { CompanyOverview } from "@/src/features/panel/CompanyOverview";
import { useActiveCompany } from "@/src/features/panel/useActiveCompany";
import { verificationColor, verificationLabel } from "@/src/features/panel/status";
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
  const pathname = usePathname();
  const id = Number(companyId);
  const { switcher, entry, loading } = useActiveCompany(id);
  const companies = switcher?.companies ?? [];

  return (
    <main className="mx-auto flex w-full max-w-[1000px] flex-1 flex-col gap-[28px] px-[16px] py-[40px] sm:px-[24px] md:px-[32px] md:py-[64px]">
      <div className="flex flex-row justify-between">
        <Typography className="text-[26px] font-semibold sm:text-[32px]" type="h1">
          {strings.companyPanel}
        </Typography>
        <Button onPress={() => router.push("/panel/new")}>
          <Plus aria-hidden className="size-4" />
          {strings.registerNewCompany}
        </Button>
      </div>

      {loading ? (
        <div className="flex flex-col gap-[16px]">
          <Skeleton className="h-[110px] rounded-[var(--radius)]" />
          <Skeleton className="h-[240px] rounded-[var(--radius)]" />
        </div>
      ) : (
        <>
          {companies.length > 1 && (
          <Tabs
            selectedKey={pathname ?? String(id)}
            variant="secondary"
            align="start"
            className="w-full"
          >
            <Tabs.ListContainer>
              <Tabs.List aria-label={strings.switchCompany}>
                {companies.map((company) => (
                  <Tabs.Tab
                    key={company.id}
                    id={String(company.id)}
                    href={`/panel/${company.id}`}
                    render={(domProps) => <NextLink {...(domProps as any)} />}
                  >
                    <div className="flex min-w-0 flex-row items-center gap-[6px] text-left">
                      <span className="block min-w-0 max-w-20 truncate" title={company.company_name}>
                        {company.company_name}
                      </span>
                      <Chip
                        color={verificationColor(company.verification_status)}
                        size="sm"
                        variant="soft"
                      >
                        {verificationLabel(company.verification_status)}
                      </Chip>
                    </div>
                    <Tabs.Indicator />
                  </Tabs.Tab>
                ))}
              </Tabs.List>
            </Tabs.ListContainer>
          </Tabs>
          )}
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
