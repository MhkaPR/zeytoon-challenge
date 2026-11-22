"use client";

import { Label, ListBox, Select } from "@heroui/react";
import { useTranslations } from "next-intl";

import { formatPersianNumber } from "@/src/lib/formatters/persian";
import { useSiteConfig } from "@/src/features/site/SiteConfigProvider";

export type SortOrder = "default" | "price" | "expensive" | "relevance";
export type SortOption = { id: SortOrder; labelKey: string };
const SORT_OPTIONS: SortOption[] = [
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
  options = SORT_OPTIONS,
}: {
  sort: SortOrder;
  onSortChange: (value: SortOrder) => void;
  pageSize: number;
  onPageSizeChange: (value: number) => void;
  options?: SortOption[];
}) {
  const ot = useTranslations();
  const config = useSiteConfig();
  const pageSizes = config.catalog.pageSizes.includes(pageSize)
    ? config.catalog.pageSizes
    : [...config.catalog.pageSizes, pageSize].sort((a, b) => a - b);
  return (
    <div className="flex flex-wrap items-center gap-[12px]">
      <div className="flex items-center gap-[7px]">
        <Label className="shrink-0 text-[11px] text-muted">{ot("sortLabel")}</Label>
        <Select aria-label={ot("sortLabel")} className="w-[145px]" value={sort} variant="primary" onChange={(value) => value && onSortChange(value as SortOrder)}>
          <Select.Trigger><Select.Value /><Select.Indicator /></Select.Trigger>
          <Select.Popover>
            <ListBox>
              {options.map((option) => <ListBox.Item id={option.id} key={option.id} textValue={ot(option.labelKey)}>{ot(option.labelKey)}<ListBox.ItemIndicator /></ListBox.Item>)}
            </ListBox>
          </Select.Popover>
        </Select>
      </div>
      <div className="flex items-center gap-[7px]">
        <Label className="shrink-0 text-[11px] text-muted">{ot("pageSizeLabel")}</Label>
        <Select
          aria-label={ot("pageSizeAria")}
          className="w-[92px]"
          value={String(pageSize)}
          variant="primary"
          onChange={(value) => value && onPageSizeChange(Number(value))}
        >
          <Select.Trigger><Select.Value /><Select.Indicator /></Select.Trigger>
          <Select.Popover>
            <ListBox>
              {pageSizes.map((size) => (
                <ListBox.Item id={String(size)} key={size} textValue={formatPersianNumber(size)}>
                  {formatPersianNumber(size)}
                  <ListBox.ItemIndicator />
                </ListBox.Item>
              ))}
            </ListBox>
          </Select.Popover>
        </Select>
      </div>
    </div>
  );
}

