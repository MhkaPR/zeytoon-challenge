"use client";

import { useTranslations } from "next-intl";

import { Button, Label, ListBox, Select, Typography } from "@heroui/react";
import { Save } from "lucide-react";
import { useState } from "react";
import type {
  ExtractedTable,
  PlanType,
  Recipe,
  RecipeBinding,
} from "@/src/lib/api/ops";
import { FieldBindingPanel } from "./FieldBindingPanel";
import { TableSwitcher } from "./TableSwitcher";

function initialBindings(recipe: Recipe | null): Record<string, RecipeBinding> {
  const result: Record<string, RecipeBinding> = {};
  for (const binding of recipe?.bindings ?? []) {
    result[binding.schema_field_key] = binding;
  }
  return result;
}

export function MappingWorkspace({
  planTypes,
  tables,
  initialRecipe,
  busy = false,
  errorText,
  onSave,
}: {
  planTypes: PlanType[];
  tables: ExtractedTable[];
  initialRecipe: Recipe | null;
  busy?: boolean;
  errorText?: string | null;
  onSave: (planType: string, bindings: RecipeBinding[]) => void;
}) {
  const ot = useTranslations();

  const [planType, setPlanType] = useState(
    initialRecipe?.plan_type ?? planTypes[0]?.key ?? "",
  );
  const [selectedTableId, setSelectedTableId] = useState<number | null>(
    tables[0]?.id ?? null,
  );
  const [bindings, setBindings] = useState<Record<string, RecipeBinding>>(() =>
    initialBindings(initialRecipe),
  );

  const plan =
    planTypes.find((candidate) => candidate.key === planType) ?? planTypes[0];
  const fields = plan?.fields ?? [];
  const selectedTable =
    tables.find((table) => table.id === selectedTableId) ?? tables[0];

  const rows = selectedTable
    ? [...selectedTable.rows].sort((a, b) => a.row_index - b.row_index)
    : [];

  const missing = fields.filter(
    (field) => field.required && !bindings[field.key]?.source_column_id,
  );

  function changePlan(next: string) {
    setPlanType(next);
    setBindings(initialBindings(initialRecipe));
  }

  function save() {
    const payload = fields
      .map((field) => bindings[field.key])
      .filter((binding): binding is RecipeBinding => Boolean(binding));
    onSave(planType, payload);
  }

  if (tables.length === 0) {
    return (
      <Typography className="text-[13px] text-warning" role="status">
        {ot("noExtractedTables")}
      </Typography>
    );
  }

  return (
    <div className="flex flex-col gap-[16px]">
      <div className="flex flex-wrap items-end gap-[12px]">
        <Select
          className="w-full max-w-[300px]"
          selectedKey={planType}
          onSelectionChange={(key) => {
            if (typeof key === "string") changePlan(key);
          }}
        >
          <Label>{ot("opsPlanType")}</Label>
          <Select.Trigger>
            <Select.Value />
            <Select.Indicator />
          </Select.Trigger>
          <Select.Popover>
            <ListBox>
              {planTypes.map((type) => (
                <ListBox.Item id={type.key} key={type.key} textValue={type.label}>
                  {type.label}
                  <ListBox.ItemIndicator />
                </ListBox.Item>
              ))}
            </ListBox>
          </Select.Popover>
        </Select>
        <TableSwitcher
          onChange={setSelectedTableId}
          selectedId={selectedTable?.id ?? null}
          tables={tables}
        />
      </div>

      <Typography className="text-[12px] text-muted">{ot("gridHint")}</Typography>
      <div className="max-h-[240px] overflow-auto rounded-[var(--radius)] border border-[var(--separator)]">
        <table className="w-full border-collapse text-start text-[13px]">
          <thead className="sticky top-0 bg-surface-secondary">
            <tr>
              {selectedTable?.columns.map((column) => (
                <th className="border-b border-[var(--separator)] px-[12px] py-[8px] font-semibold" key={column.id} scope="col">
                  {column.label || column.column_id}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.row_index}>
                {selectedTable?.columns.map((column) => (
                  <td className="border-b border-[var(--separator)] px-[12px] py-[8px]" key={column.id}>
                    {row.cells[column.column_id] ?? ""}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <FieldBindingPanel
        bindings={bindings}
        fields={fields}
        onChange={(fieldKey, binding) =>
          setBindings((previous) => ({ ...previous, [fieldKey]: binding }))
        }
        tables={tables}
      />

      {missing.length > 0 && (
        <Typography className="text-[12px] text-warning" role="status">
          {ot("recipeIncomplete")}: {missing.map((field) => field.label).join("، ")}
        </Typography>
      )}
      {errorText && (
        <Typography className="text-[12px] text-danger" role="alert">
          {errorText}
        </Typography>
      )}

      <Button
        className="self-start"
        isDisabled={busy || missing.length > 0}
        onPress={save}
      >
        <Save aria-hidden className="size-4" />
        {busy ? ot("saving") : ot("saveRecipe")}
      </Button>
    </div>
  );
}
