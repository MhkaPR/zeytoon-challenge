"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";

import { PlanPagination } from "@/src/features/home/planCatalog/CatalogControls";

/** Navigates the server-rendered company directory between pages. */
export function CompanyPagination({
  page,
  totalPages,
  query,
}: {
  page: number;
  totalPages: number;
  query: string;
}) {
  const ot = useTranslations();
  const router = useRouter();

  return (
    <PlanPagination
      ariaLabel={ot("companiesPaginationLabel")}
      page={page}
      totalPages={totalPages}
      onPageChange={(next) => {
        const params = new URLSearchParams();
        if (query) params.set("q", query);
        if (next > 1) params.set("page", String(next));
        const search = params.toString();
        router.push(search ? `/companies?${search}` : "/companies");
      }}
    />
  );
}
