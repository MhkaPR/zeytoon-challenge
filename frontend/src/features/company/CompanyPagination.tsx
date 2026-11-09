"use client";

import { Pagination } from "@heroui/react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";

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
  if (totalPages <= 1) return null;

  const pages: (number | "ellipsis")[] = [];
  if (totalPages <= 7) {
    pages.push(...Array.from({ length: totalPages }, (_, index) => index + 1));
  } else {
    pages.push(1);
    if (page > 3) pages.push("ellipsis");
    for (
      let current = Math.max(2, page - 1);
      current <= Math.min(totalPages - 1, page + 1);
      current += 1
    ) {
      pages.push(current);
    }
    if (page < totalPages - 2) pages.push("ellipsis");
    pages.push(totalPages);
  }

  function goTo(next: number) {
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (next > 1) params.set("page", String(next));
    const search = params.toString();
    router.push(search ? `/companies?${search}` : "/companies");
  }

  return (
    <Pagination aria-label={ot("companiesPaginationLabel")} className="justify-center" size="sm">
      <Pagination.Content>
        <Pagination.Item>
          <Pagination.Previous isDisabled={page === 1} onPress={() => goTo(page - 1)}>
            <Pagination.PreviousIcon />
            <span>{ot("previousPage")}</span>
          </Pagination.Previous>
        </Pagination.Item>
        {pages.map((item, index) =>
          item === "ellipsis" ? (
            <Pagination.Item key={`ellipsis-${index}`}>
              <Pagination.Ellipsis />
            </Pagination.Item>
          ) : (
            <Pagination.Item key={item}>
              <Pagination.Link isActive={item === page} onPress={() => goTo(item)}>
                {item.toLocaleString("fa-IR")}
              </Pagination.Link>
            </Pagination.Item>
          ),
        )}
        <Pagination.Item>
          <Pagination.Next isDisabled={page === totalPages} onPress={() => goTo(page + 1)}>
            <span>{ot("nextPage")}</span>
            <Pagination.NextIcon />
          </Pagination.Next>
        </Pagination.Item>
      </Pagination.Content>
    </Pagination>
  );
}
