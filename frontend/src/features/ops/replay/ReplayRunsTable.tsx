"use client";

import { Typography } from "@heroui/react";

import type { ReplayRun } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";

export function ReplayRunsTable({ runs }: { runs: ReplayRun[] }) {
  if (runs.length === 0) {
    return (
      <Typography className="text-[13px] text-muted" role="status">
        {opsStrings.noReplayRuns}
      </Typography>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-right text-[12px]">
        <thead>
          <tr className="border-b border-[var(--ds-border)] text-muted">
            <th className="py-[6px] font-medium">#</th>
            <th className="py-[6px] font-medium">{opsStrings.status}</th>
            <th className="py-[6px] font-medium">{opsStrings.beforeTrace}</th>
            <th className="py-[6px] font-medium">{opsStrings.afterTrace}</th>
            <th className="py-[6px] font-medium">{opsStrings.applied}</th>
            <th className="py-[6px] font-medium">{opsStrings.skipped}</th>
            <th className="py-[6px] font-medium">{opsStrings.failed}</th>
            <th className="py-[6px] font-medium">{opsStrings.diffSummary}</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr className="border-b border-[var(--ds-border)]" key={run.id}>
              <td className="py-[8px]">
                {run.id} / {run.link_id}
              </td>
              <td className="py-[8px]">{run.state}</td>
              <td className="py-[8px]">{run.before_trace_id ?? opsStrings.none}</td>
              <td className="py-[8px]">{run.after_trace_id ?? opsStrings.none}</td>
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
