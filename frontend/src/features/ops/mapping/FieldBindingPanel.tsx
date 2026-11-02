"use client";

import {
  Chip,
  Input,
  Label,
  ListBox,
  Select,
  TextField,
  Typography,
} from "@heroui/react";

import type {
  ExtractedTable,
  PlanSchemaField,
  RecipeBinding,
} from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";

export function emptyBinding(fieldKey: string): RecipeBinding {
  return {
    schema_field_key: fieldKey,
    source_table_id: null,
    source_column_id: null,
    selector: "",
    formula: "",
    aggregation: "",
  };
}

/** Resolve a selected column id against every table, enabling cross-table merges. */
export function resolveColumnBinding(
  tables: ExtractedTable[],
  columnId: number,
): { tableId: number; selector: string } | null {
  for (const table of tables) {
    const column = table.columns.find((candidate) => candidate.id === columnId);
    if (column) return { tableId: table.id, selector: column.path };
  }
  return null;
}

export function FieldBindingPanel({
  fields,
  tables,
  bindings,
  onChange,
}: {
  fields: PlanSchemaField[];
  tables: ExtractedTable[];
  bindings: Record<string, RecipeBinding>;
  onChange: (fieldKey: string, binding: RecipeBinding) => void;
}) {
  return (
    <div className="flex flex-col gap-[12px]">
      {fields.map((field) => {
        const binding = bindings[field.key] ?? emptyBinding(field.key);
        const selectedColumn = binding.source_column_id;
        return (
          <div
            className="flex flex-col gap-[8px] rounded-[var(--radius)] border border-[var(--ds-border)] p-[12px]"
            key={field.key}
          >
            <div className="flex flex-wrap items-center gap-[8px]">
              <Typography className="text-[14px] font-semibold">{field.label}</Typography>
              <Chip
                color={field.required ? "warning" : "default"}
                size="sm"
                variant="soft"
              >
                {field.required ? opsStrings.requiredField : opsStrings.optionalField}
              </Chip>
              {field.unit_family && (
                <span className="text-[11px] text-muted">{field.unit_family}</span>
              )}
            </div>

            <div className="grid gap-[8px] sm:grid-cols-2">
              <Select
                className="w-full"
                selectedKey={selectedColumn === null ? "none" : String(selectedColumn)}
                onSelectionChange={(key) => {
                  if (typeof key !== "string") return;
                  if (key === "none") {
                    onChange(field.key, {
                      ...binding,
                      source_column_id: null,
                      source_table_id: null,
                      selector: "",
                    });
                    return;
                  }
                  const columnId = Number(key);
                  const resolved = resolveColumnBinding(tables, columnId);
                  onChange(field.key, {
                    ...binding,
                    source_column_id: columnId,
                    source_table_id: resolved?.tableId ?? null,
                    selector: resolved?.selector ?? "",
                  });
                }}
              >
                <Label>{opsStrings.sourceColumn}</Label>
                <Select.Trigger>
                  <Select.Value />
                  <Select.Indicator />
                </Select.Trigger>
                <Select.Popover>
                  <ListBox>
                    <ListBox.Item id="none" textValue={opsStrings.none}>
                      {opsStrings.none}
                      <ListBox.ItemIndicator />
                    </ListBox.Item>
                    {tables.flatMap((table, tableIndex) =>
                      table.columns.map((column) => (
                        <ListBox.Item
                          id={String(column.id)}
                          key={column.id}
                          textValue={`${table.title || tableIndex + 1}: ${
                            column.label || column.column_id
                          }`}
                        >
                          {(table.title ||
                            `${opsStrings.tablesTitle} #${tableIndex + 1}`) +
                            " / " +
                            (column.label || column.column_id)}
                          <ListBox.ItemIndicator />
                        </ListBox.Item>
                      )),
                    )}
                  </ListBox>
                </Select.Popover>
              </Select>

              <TextField
                name={`formula-${field.key}`}
                value={binding.formula}
                onChange={(value) => onChange(field.key, { ...binding, formula: value })}
              >
                <Label>{opsStrings.formula}</Label>
                <Input dir="ltr" placeholder="=A2*B2" />
              </TextField>
            </div>

            <Typography className="text-[11px] text-muted" dir="ltr">
              {opsStrings.selector}: {binding.selector || opsStrings.none}
            </Typography>
          </div>
        );
      })}
    </div>
  );
}
