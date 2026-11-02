"use client";

import { Button, Card, Chip, Typography } from "@heroui/react";
import { Sparkles, Table2 } from "lucide-react";
import NextLink from "next/link";

import type { ExtractedTable } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";

import { StageBadge } from "../pipeline/StageBadge";

export function TableList({
  tables,
  stage,
  traceStored,
  labelingEnabled = false,
  busy = false,
  onExtract,
  onLabel,
}: {
  tables: ExtractedTable[];
  stage: string;
  traceStored: boolean;
  labelingEnabled?: boolean;
  busy?: boolean;
  onExtract: () => void;
  onLabel: () => void;
}) {
  return (
    <div className="flex flex-col gap-[16px]">
      <div className="flex flex-wrap items-center gap-[8px]">
        <StageBadge stage={stage} />
        {tables.length === 0 && (
          <Chip color="danger" size="sm" variant="soft">
            {opsStrings.flagged}
          </Chip>
        )}
      </div>

      <div className="flex flex-wrap gap-[8px]">
        <Button isDisabled={busy || !traceStored} onPress={onExtract}>
          <Table2 aria-hidden className="size-4" />
          {busy ? opsStrings.extracting : opsStrings.extractTables}
        </Button>
        <Button
          isDisabled={busy || !labelingEnabled || tables.length === 0}
          onPress={onLabel}
          variant="secondary"
        >
          <Sparkles aria-hidden className="size-4" />
          {busy ? opsStrings.labeling : opsStrings.runLabeling}
        </Button>
      </div>

      {!traceStored && (
        <Typography className="text-[13px] text-warning" role="status">
          {opsStrings.extractHint}
        </Typography>
      )}

      {!labelingEnabled && (
        <Typography className="text-[12px] text-muted">
          {opsStrings.labelingDisabled}{" "}
          <NextLink className="underline" href="/ops/settings">
            {opsStrings.navSettings}
          </NextLink>
        </Typography>
      )}

      {tables.length === 0 ? (
        <Card className="flex flex-col gap-[8px] p-[20px]" variant="secondary">
          <Typography className="text-[14px] font-medium text-danger" role="status">
            {opsStrings.noTables}
          </Typography>
          <Typography className="text-[12px] text-muted">{opsStrings.labelingHint}</Typography>
        </Card>
      ) : (
        <div className="flex flex-col gap-[16px]">
          {tables.map((table, index) => (
            <Card className="flex flex-col gap-[12px] p-[20px]" key={table.id} variant="default">
              <div className="flex flex-wrap items-center justify-between gap-[8px]">
                <div className="flex items-center gap-[8px]">
                  <Table2 aria-hidden className="size-4 text-muted" />
                  <Typography className="text-[15px] font-semibold" type="h3">
                    {table.title || `${opsStrings.tablesTitle} #${index + 1}`}
                  </Typography>
                </div>
                <div className="flex items-center gap-[8px] text-[12px] text-muted">
                  <Chip size="sm" variant="soft">
                    {opsStrings.score}: {table.score.toFixed(2)}
                  </Chip>
                  <span>
                    {opsStrings.rows}: {table.row_count}
                  </span>
                  <span>
                    {opsStrings.columns}: {table.column_count}
                  </span>
                </div>
              </div>
              {table.purpose && (
                <Typography className="text-[12px] text-muted">{table.purpose}</Typography>
              )}
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-right text-[12px]">
                  <thead>
                    <tr className="border-b border-[var(--ds-border)] text-muted">
                      <th className="py-[6px] font-medium">{opsStrings.columns}</th>
                      <th className="py-[6px] font-medium">{opsStrings.columnPath}</th>
                      <th className="py-[6px] font-medium">{opsStrings.coverage}</th>
                      <th className="py-[6px] font-medium">{opsStrings.labels}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {table.columns.map((column) => (
                      <tr className="border-b border-[var(--ds-border)]" key={column.id}>
                        <td className="py-[8px]">{column.label || column.column_id}</td>
                        <td className="py-[8px]" dir="ltr">
                          {column.path}
                        </td>
                        <td className="py-[8px]">{Math.round(column.coverage * 100)}%</td>
                        <td className="py-[8px]">{column.labels.join("، ") || opsStrings.none}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
