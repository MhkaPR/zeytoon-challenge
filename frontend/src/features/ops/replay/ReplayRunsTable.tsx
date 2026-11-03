"use client";

import { useTranslations } from "next-intl";
import { Typography } from "@heroui/react";

import type { ReplayRun } from "@/src/lib/api/ops";
export function ReplayRunsTable({ runs }: { runs: ReplayRun[] }) {
  const ot = useTranslations();
  if (runs.length === 0) {
    return (
      <Typography className="text-[13px] text-muted" role="status">
        {ot("noReplayRuns")}
      </Typography>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-right text-[12px]">
        <thead>
          <tr className="border-b border-[var(--ds-border)] text-muted">
            <th className="py-[6px] font-medium">#</th>
            <th className="py-[6px] font-medium">{ot("status")}</th>
            <th className="py-[6px] font-medium">{ot("beforeTrace")}</th>
            <th className="py-[6px] font-medium">{ot("afterTrace")}</th>
            <th className="py-[6px] font-medium">{ot("applied")}</th>
            <th className="py-[6px] font-medium">{ot("skipped")}</th>
            <th className="py-[6px] font-medium">{ot("failed")}</th>
            <th className="py-[6px] font-medium">{ot("diffSummary")}</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr className="border-b border-[var(--ds-border)]" key={run.id}>
              <td className="py-[8px]">
                {run.id} / {run.link_id}
              </td>
              <td className="py-[8px]">{run.state}</td>
              <td className="py-[8px]">{run.before_trace_id ?? ot("none")}</td>
              <td className="py-[8px]">{run.after_trace_id ?? ot("none")}</td>
              <td className="py-[8px]">{run.stats_applied}</td>
              <td className="py-[8px]">{run.stats_skipped}</td>
              <td className="py-[8px]">{run.stats_failed}</td>
              <td className="max-w-[260px] truncate py-[8px]" dir="ltr">
                {JSON.stringify(run.diff_summary)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
