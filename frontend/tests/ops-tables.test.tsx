import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TableList } from "@/src/features/ops/tables/TableList";
import type { ExtractedTable } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";

afterEach(() => {
  vi.restoreAllMocks();
});

const table: ExtractedTable = {
  id: 31,
  score: 0.87,
  row_count: 2,
  column_count: 2,
  parent: "",
  meta: {},
  title: "Plans",
  purpose: "Hosting plans",
  columns: [
    {
      id: 101,
      column_id: "A",
      label: "Name",
      path: "table/tr/td[1]",
      atype: "string",
      slot: "",
      coverage: 1,
      row_count: 2,
      labels: ["Plan name"],
    },
    {
      id: 102,
      column_id: "B",
      label: "Price",
      path: "table/tr/td[2]",
      atype: "number",
      slot: "",
      coverage: 0.75,
      row_count: 2,
      labels: [],
    },
  ],
  rows: [],
};

describe("table list", () => {
  it("shows candidate tables with score, column paths, and labels", () => {
    render(
      <TableList
        labelingEnabled
        onExtract={vi.fn()}
        onLabel={vi.fn()}
        stage="extracted"
        tables={[table]}
        traceStored
      />,
    );

    expect(screen.getByText("Plans")).toBeInTheDocument();
    expect(screen.getByText(/0.87/)).toBeInTheDocument();
    expect(screen.getByText("table/tr/td[1]")).toBeInTheDocument();
    expect(screen.getByText("Plan name")).toBeInTheDocument();
  });

  it("flags the link when extraction yields no tables", () => {
    render(
      <TableList
        onExtract={vi.fn()}
        onLabel={vi.fn()}
        stage="flagged"
        tables={[]}
        traceStored
      />,
    );

    expect(screen.getByText(opsStrings.flagged)).toBeInTheDocument();
    expect(screen.getByText(opsStrings.noTables)).toBeInTheDocument();
  });
});
