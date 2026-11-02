"use client";

import { Label, ListBox, Pagination, Select } from "@heroui/react";

type SortOrder = "default" | "price" | "expensive";
const PAGE_SIZES = [8, 12, 20] as const;
const SORT_OPTIONS: { id: SortOrder; label: string }[] = [
  { id: "default", label: "ترتیب پیش‌فرض" },
  { id: "price", label: "ارزان‌ترین" },
  { id: "expensive", label: "گران‌ترین" },
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
  return (
    <div className="flex flex-wrap items-center gap-[12px]">
      <div className="flex items-center gap-[7px]">
        <Label className="shrink-0 text-[11px] text-muted">مرتب‌سازی</Label>
        <Select aria-label="مرتب‌سازی" className="w-[145px]" value={sort} variant="primary" onChange={(value) => value && onSortChange(value as SortOrder)}>
          <Select.Trigger><Select.Value /><Select.Indicator /></Select.Trigger>
          <Select.Popover>
            <ListBox>
              {SORT_OPTIONS.map((option) => <ListBox.Item id={option.id} key={option.id} textValue={option.label}>{option.label}<ListBox.ItemIndicator /></ListBox.Item>)}
            </ListBox>
          </Select.Popover>
        </Select>
      </div>
      <div className="flex items-center gap-[7px]">
        <Label className="shrink-0 text-[11px] text-muted">نمایش</Label>
        <Select aria-label="تعداد پلن در هر صفحه" className="w-[82px]" value={String(pageSize)} variant="primary" onChange={(value) => value && onPageSizeChange(Number(value))}>
          <Select.Trigger><Select.Value /><Select.Indicator /></Select.Trigger>
          <Select.Popover>
            <ListBox>
              {PAGE_SIZES.map((size) => <ListBox.Item id={String(size)} key={size} textValue={String(size)}>{size.toLocaleString("fa-IR")} پلن<ListBox.ItemIndicator /></ListBox.Item>)}
            </ListBox>
          </Select.Popover>
        </Select>
      </div>
    </div>
  );
}

/** HeroUI pagination control for the current filtered result set. */
export function PlanPagination({ page, totalPages, onPageChange }: { page: number; totalPages: number; onPageChange: (page: number) => void }) {
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
    <Pagination aria-label="صفحه‌بندی پلن‌ها" className="justify-center" size="sm">
      <Pagination.Content>
        <Pagination.Item>
          <Pagination.Previous isDisabled={page === 1} onPress={() => onPageChange(page - 1)}>
            <Pagination.PreviousIcon /><span>قبلی</span>
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
            <span>بعدی</span><Pagination.NextIcon />
          </Pagination.Next>
        </Pagination.Item>
      </Pagination.Content>
    </Pagination>
  );
}

