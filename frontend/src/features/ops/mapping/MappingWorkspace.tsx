"use client";

import "handsontable/styles/handsontable.min.css";
import "handsontable/styles/ht-theme-main.css";

import { HotTable } from "@handsontable/react-wrapper";
import { Button, Card, Label, ListBox, Select, Typography } from "@heroui/react";
import { useMemo, useState } from "react";

import type {
  ExtractedTable,
  PlanType,
  Recipe,
  RecipeBinding,
} from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";

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

  const grid = useMemo(() => {
    if (!selectedTable) return { data: [], headers: [] as string[] };
    const headers = selectedTable.columns.map(
      (column) => column.label || column.column_id,
    );
    const rows = [...selectedTable.rows].sort((a, b) => a.row_index - b.row_index);
    return {
      headers,
      data: rows.map((row) =>
        selectedTable.columns.map((column) => row.cells[column.column_id] ?? ""),
      ),
    };
  }, [selectedTable]);

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
        {opsStrings.noExtractedTables}
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
          <Label>{opsStrings.planType}</Label>
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

      <Card className="flex flex-col gap-[8px] p-[12px]" variant="secondary">
        <Typography className="text-[12px] text-muted">{opsStrings.gridHint}</Typography>
        <div className="overflow-x-auto">
          <HotTable
            className="ht-theme-main"
            colHeaders={grid.headers}
            data={grid.data}
            height={240}
            licenseKey="non-commercial-and-evaluation"
            readOnly
            rowHeaders
            stretchH="all"
          />
        </div>
      </Card>

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
          {opsStrings.recipeIncomplete}: {missing.map((field) => field.label).join("، ")}
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
        {busy ? opsStrings.saving : opsStrings.saveRecipe}
      </Button>
    </div>
  );
}
