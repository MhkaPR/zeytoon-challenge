"use client";

import { Label, ListBox, Pagination, Select } from "@heroui/react";
import { useTranslations } from "next-intl";

import { useSiteConfig } from "@/src/features/site/SiteConfigProvider";

type SortOrder = "default" | "price" | "expensive";
const SORT_OPTIONS: { id: SortOrder; labelKey: string }[] = [
  { id: "default", labelKey: "sortDefault" },
  { id: "price", labelKey: "sortPriceAsc" },
  { id: "expensive", labelKey: "sortPriceDesc" },
];

/** Compact HeroUI sort and page-size controls. */
export function SortAndPageSizeControls({
  sort,
  onSortChange,
  pageSize,
  onPageSizeChange,
}: {
  sort: SortOrder;
  onSortChange: (value: SortOrder) => void;
  pageSize: number;
  onPageSizeChange: (value: number) => void;
}) {
  const ot = useTranslations();
  const config = useSiteConfig();
  return (
    <div className="flex flex-wrap items-center gap-[12px]">
      <div className="flex items-center gap-[7px]">
        <Label className="shrink-0 text-[11px] text-muted">{ot("sortLabel")}</Label>
        <Select aria-label={ot("sortLabel")} className="w-[145px]" value={sort} variant="primary" onChange={(value) => value && onSortChange(value as SortOrder)}>
          <Select.Trigger><Select.Value /><Select.Indicator /></Select.Trigger>
          <Select.Popover>
            <ListBox>
              {SORT_OPTIONS.map((option) => <ListBox.Item id={option.id} key={option.id} textValue={ot(option.labelKey)}>{ot(option.labelKey)}<ListBox.ItemIndicator /></ListBox.Item>)}
            </ListBox>
          </Select.Popover>
        </Select>
      </div>
    </div>
  );
}

/** HeroUI pagination control for the current filtered result set. */
export function PlanPagination({
  page,
  totalPages,
  onPageChange,
  ariaLabel,
}: {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  ariaLabel?: string;
}) {
  const ot = useTranslations();
  if (totalPages <= 1) return null;
  const pages: (number | "ellipsis")[] = [];
  if (totalPages <= 7) {
    pages.push(...Array.from({ length: totalPages }, (_, index) => index + 1));
  } else {
    pages.push(1);
    if (page > 3) pages.push("ellipsis");
    for (let current = Math.max(2, page - 1); current <= Math.min(totalPages - 1, page + 1); current += 1) pages.push(current);
    if (page < totalPages - 2) pages.push("ellipsis");
    pages.push(totalPages);
  }

  return (
    <Pagination aria-label={ariaLabel ?? ot("paginationLabel")} className="justify-center" size="sm">
      <Pagination.Content>
        <Pagination.Item>
          <Pagination.Previous isDisabled={page === 1} onPress={() => onPageChange(page - 1)}>
            <Pagination.PreviousIcon /><span>{ot("previousPage")}</span>
          </Pagination.Previous>
        </Pagination.Item>
        {pages.map((item, index) => item === "ellipsis" ? (
          <Pagination.Item key={`ellipsis-${index}`}><Pagination.Ellipsis /></Pagination.Item>
        ) : (
          <Pagination.Item key={item}>
            <Pagination.Link isActive={item === page} onPress={() => onPageChange(item)}>{item.toLocaleString("fa-IR")}</Pagination.Link>
          </Pagination.Item>
        ))}
        <Pagination.Item>
          <Pagination.Next isDisabled={page === totalPages} onPress={() => onPageChange(page + 1)}>
            <span>{ot("nextPage")}</span><Pagination.NextIcon />
          </Pagination.Next>
        </Pagination.Item>
      </Pagination.Content>
    </Pagination>
  );
}

