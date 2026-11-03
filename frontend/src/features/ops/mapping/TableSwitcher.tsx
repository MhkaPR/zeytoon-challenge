"use client";

import { useTranslations } from "next-intl";
import { Label, ListBox, Select } from "@heroui/react";

import type { ExtractedTable } from "@/src/lib/api/ops";
export function TableSwitcher({
  tables,
  selectedId,
  onChange,
}: {
  tables: ExtractedTable[];
  selectedId: number | null;
  onChange: (tableId: number) => void;
}) {
  const ot = useTranslations();
  return (
    <Select
      className="w-full max-w-[360px]"
      selectedKey={selectedId === null ? null : String(selectedId)}
      onSelectionChange={(key) => {
        if (typeof key === "string") onChange(Number(key));
      }}
    >
      <Label>{ot("sourceTable")}</Label>
      <Select.Trigger>
        <Select.Value />
        <Select.Indicator />
      </Select.Trigger>
      <Select.Popover>
        <ListBox>
          {tables.map((table, index) => (
            <ListBox.Item
              id={String(table.id)}
              key={table.id}
              textValue={table.title || `Table ${index + 1}`}
            >
              {table.title || `${ot("tablesTitle")} #${index + 1}`}
              <ListBox.ItemIndicator />
            </ListBox.Item>
          ))}
        </ListBox>
      </Select.Popover>
    </Select>
  );
}
