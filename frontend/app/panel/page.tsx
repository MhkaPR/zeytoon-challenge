"use client";

import { Typography } from "@heroui/react";
import { useRouter } from "next/navigation";

import { CompanyForm } from "@/src/features/company/CompanyForm";
import { CompanySwitcher } from "@/src/features/panel/CompanySwitcher";
import { EmptyState } from "@/src/features/panel/EmptyState";
import { useActiveCompany } from "@/src/features/panel/useActiveCompany";
import { strings } from "@/src/lib/i18n/strings";

/**
 * Panel shell: shows the empty state with a "Register new company" button when the user owns
 * no companies, otherwise the company switcher (FR-022, FR-023).
 */
export default function PanelPage() {
  const router = useRouter();
  const { switcher, loading } = useActiveCompany();

  return (
    <main className="mx-auto flex w-full max-w-[1000px] flex-1 flex-col gap-[32px] px-[32px] py-[64px]">
      <Typography className="text-[40px] font-semibold" type="h1">
        {strings.companyPanel}
      </Typography>
      {loading ? null : switcher?.empty_state ? (
        <EmptyState onRegister={() => router.push("/panel/new")} />
      ) : (
        <>
          <CompanySwitcher companies={switcher?.companies ?? []} />
          <Typography className="text-[24px] font-semibold" type="h2">
            {strings.registerNewCompany}
          </Typography>
          <CompanyForm onCreated={(id) => router.push(`/panel/${id}`)} />
        </>
      )}
    </main>
  );
}
