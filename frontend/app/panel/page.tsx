"use client";

import { useTranslations } from "next-intl";
import { Button, Skeleton, Typography } from "@heroui/react";
import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";

import { CompanySwitcher } from "@/src/features/panel/CompanySwitcher";
import { EmptyState } from "@/src/features/panel/EmptyState";
import { useActiveCompany } from "@/src/features/panel/useActiveCompany";
/**
 * Panel shell: shows the empty state with a "Register new company" button when the user owns
 * no companies, otherwise the company switcher plus the register action (FR-022, FR-023).
 */
export default function PanelPage() {
  const ot = useTranslations();
  const router = useRouter();
  const { switcher, loading } = useActiveCompany();
  const companies = switcher?.companies ?? [];

  return (
    <main className="mx-auto flex w-full max-w-[1000px] flex-1 flex-col gap-[32px] px-[16px] py-[40px] sm:px-[24px] md:px-[32px] md:py-[64px]">
      <header className="flex flex-wrap items-end justify-between gap-[16px]">
        <div className="flex flex-col gap-[6px]">
          <Typography className="text-[28px] font-semibold sm:text-[34px]" type="h1">
            {ot("companyPanel")}
          </Typography>
          <Typography className="max-w-[560px] text-[14px] leading-[1.8]" color="muted">
            {ot("panelSubtitle")}
          </Typography>
        </div>
        {!loading && companies.length > 0 && (
          <Button onPress={() => router.push("/panel/new")}>
            <Plus aria-hidden className="size-4" />
            {ot("registerNewCompany")}
          </Button>
        )}
      </header>

      {loading ? (
        <div className="flex flex-col gap-[16px]">
          <Skeleton className="h-[110px] rounded-[var(--radius)]" />
          <Skeleton className="h-[120px] rounded-[var(--radius)]" />
        </div>
      ) : companies.length === 0 ? (
        <EmptyState onRegister={() => router.push("/panel/new")} />
      ) : (
        <div className="flex flex-col gap-[24px]">
          <Typography className="text-[18px] font-semibold" type="h2">
            {ot("panelCompaniesTitle")}
          </Typography>
          <CompanySwitcher companies={companies} />
        </div>
      )}
    </main>
  );
}
