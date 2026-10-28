"use client";

import { Card, Typography } from "@heroui/react";
import NextLink from "next/link";

import type { Link } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";

import { StageBadge } from "../pipeline/StageBadge";

const REVIEW_LABEL: Record<string, string> = {
  candidate: opsStrings.reviewCandidate,
  kept: opsStrings.reviewKept,
  removed: opsStrings.reviewRemoved,
};

/** The links already stored for a site, so manual additions are visibly recorded. */
export function LinkList({ links }: { links: Link[] }) {
  if (links.length === 0) {
    return (
      <Typography className="text-[13px] text-warning" role="status">
        {opsStrings.linksListEmpty}
      </Typography>
    );
  }

  return (
    <Card className="flex flex-col gap-[12px] p-[20px]" variant="default">
      <Typography className="text-[16px] font-semibold" type="h3">
        {opsStrings.linksListTitle}
      </Typography>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-right text-[13px]">
          <thead>
            <tr className="border-b border-[var(--ds-border)] text-muted">
              <th className="py-[8px] font-medium">URL</th>
              <th className="py-[8px] font-medium">{opsStrings.status}</th>
              <th className="py-[8px] font-medium">{opsStrings.reviewState}</th>
              <th className="py-[8px] font-medium">{opsStrings.action}</th>
            </tr>
          </thead>
          <tbody>
            {links.map((link) => (
              <tr className="border-b border-[var(--ds-border)]" key={link.id}>
                <td className="max-w-[420px] truncate py-[10px]" dir="ltr" title={link.url}>
                  {link.url}
                </td>
                <td className="py-[10px]">
                  <StageBadge stage={link.pipeline_stage} />
                </td>
                <td className="py-[10px]">
                  {REVIEW_LABEL[link.review_state] ?? link.review_state}
                </td>
                <td className="py-[10px]">
                  {link.review_state === "kept" ? (
                    <NextLink
                      className="rounded-[var(--radius)] bg-accent px-[10px] py-[6px] text-[12px] font-medium text-accent-foreground"
                      href={`/ops/links/${link.id}/capture`}
                    >
                      {opsStrings.openCapture}
                    </NextLink>
                  ) : (
                    <span className="text-[12px] text-muted">{opsStrings.none}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
