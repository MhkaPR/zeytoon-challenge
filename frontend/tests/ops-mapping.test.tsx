import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  FieldBindingPanel,
  resolveColumnBinding,
} from "@/src/features/ops/mapping/FieldBindingPanel";
import { MappingWorkspace } from "@/src/features/ops/mapping/MappingWorkspace";
import type { ExtractedTable, PlanType, Recipe } from "@/src/lib/api/ops";
import { opsStrings } from "./messages";

afterEach(() => {
  vi.restoreAllMocks();
});

const tables: ExtractedTable[] = [
  {
    id: 1,
    score: 0.9,
    row_count: 1,
    column_count: 1,
    parent: "",
    meta: {},
    title: "Names",
    purpose: "",
    columns: [
      {
        id: 11,
        column_id: "A",
        label: "Name",
        path: "table[1]/td[1]",
        atype: "string",
        slot: "",
        coverage: 1,
        row_count: 1,
        labels: [],
      },
    ],
    rows: [{ row_index: 0, cells: { A: "Basic" } }],
  },
  {
    id: 2,
    score: 0.8,
    row_count: 1,
    column_count: 1,
    parent: "",
    meta: {},
    title: "Prices",
    purpose: "",
    columns: [
      {
        id: 21,
        column_id: "B",
        label: "Price",
        path: "table[2]/td[1]",
        atype: "number",
        slot: "",
        coverage: 1,
        row_count: 1,
        labels: [],
      },
    ],
    rows: [{ row_index: 0, cells: { B: "120000" } }],
  },
];

const planTypes: PlanType[] = [
  {
    key: "hosting",
    label: "هاست",
    fields: [
      {
        key: "name",
        label: "نام",
        kind: "string",
        required: true,
        unit_family: null,
        values: [],
      },
      {
        key: "price",
        label: "قیمت",
        kind: "number",
        required: true,
        unit_family: "currency",
        values: [],
      },
    ],
  },
];

const completeRecipe: Recipe = {
  id: 5,
  plan_type: "hosting",
  version: 2,
  is_complete: true,
  bindings: [
    {
      schema_field_key: "name",
      source_table_id: 1,
      source_column_id: 11,
      selector: "table[1]/td[1]",
      formula: "=A2",
      aggregation: "",
    },
    {
      schema_field_key: "price",
      source_table_id: 2,
      source_column_id: 21,
      selector: "table[2]/td[1]",
      formula: "=B2",
      aggregation: "",
    },
  ],
};

describe("mapping workspace", () => {
  it("blocks saving while required fields are unconnected", () => {
    render(
      <MappingWorkspace
        initialRecipe={null}
        onSave={vi.fn()}
        planTypes={planTypes}
        tables={tables}
      />,
    );

    expect(screen.getByText(new RegExp(opsStrings.recipeIncomplete))).toBeInTheDocument();
    expect(screen.getByRole("button", { name: opsStrings.saveRecipe })).toBeDisabled();
  });

  it("restores saved selectors and formulas on reopen", () => {
    render(
      <MappingWorkspace
        initialRecipe={completeRecipe}
        onSave={vi.fn()}
        planTypes={planTypes}
        tables={tables}
      />,
    );

    const formulas = screen.getAllByDisplayValue(/=/) as HTMLInputElement[];
    expect(formulas.map((input) => input.value)).toEqual(["=A2", "=B2"]);
    expect(screen.getByText(/table\[2\]\/td\[1\]/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: opsStrings.saveRecipe })).toBeEnabled();
  });

  it("resolves a column from a second table for cross-table merging", () => {
    expect(resolveColumnBinding(tables, 21)).toEqual({
      tableId: 2,
      selector: "table[2]/td[1]",
    });
  });

  it("switches the preview to another source table", async () => {
    const user = userEvent.setup();
    render(
      <MappingWorkspace
        initialRecipe={null}
        onSave={vi.fn()}
        planTypes={planTypes}
        tables={tables}
      />,
    );

    expect(screen.getByRole("table")).toHaveTextContent("Basic");
    const selects = document.querySelectorAll("select");
    expect(selects.length).toBeGreaterThan(1);
    await user.selectOptions(selects[1] as HTMLSelectElement, "2");
    expect(screen.getByRole("table")).toHaveTextContent("120000");
  });

  it("shows every saved binding in the field panel", () => {
    render(
      <FieldBindingPanel
        bindings={{
          name: completeRecipe.bindings[0],
          price: completeRecipe.bindings[1],
        }}
        fields={planTypes[0].fields}
        onChange={vi.fn()}
        tables={tables}
      />,
    );
    expect(screen.getByText("نام")).toBeInTheDocument();
    expect(screen.getByText("قیمت")).toBeInTheDocument();
  });
});
