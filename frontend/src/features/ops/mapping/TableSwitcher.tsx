"use client";

import { Label, ListBox, Select } from "@heroui/react";

import type { ExtractedTable } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";

export function TableSwitcher({
  tables,
  selectedId,
  onChange,
}: {
  tables: ExtractedTable[];
  selectedId: number | null;
  onChange: (tableId: number) => void;
}) {
  return (
    <Select
      className="w-full max-w-[360px]"
      selectedKey={selectedId === null ? null : String(selectedId)}
      onSelectionChange={(key) => {
        if (typeof key === "string") onChange(Number(key));
      }}
    >
      <Label>{opsStrings.sourceTable}</Label>
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
              {table.title || `${opsStrings.tablesTitle} #${index + 1}`}
              <ListBox.ItemIndicator />
            </ListBox.Item>
          ))}
        </ListBox>
      </Select.Popover>
    </Select>
  );
}
