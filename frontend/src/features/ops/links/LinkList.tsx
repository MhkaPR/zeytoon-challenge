"use client";

import { Button, Card, Typography } from "@heroui/react";
import { useEffect, useState } from "react";
import NextLink from "next/link";

import { getAccessToken } from "@/src/lib/session";
import { rerunLink, type Link } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";

import { StageBadge } from "../pipeline/StageBadge";

const REVIEW_LABEL: Record<string, string> = {
  candidate: opsStrings.reviewCandidate,
  kept: opsStrings.reviewKept,
  removed: opsStrings.reviewRemoved,
};

/** The links already stored for a site, so manual additions are visibly recorded. */
export function LinkList({ links }: { links: Link[] }) {
  const [retrying, setRetrying] = useState<Set<number>>(() => new Set());
  const [queued, setQueued] = useState<Set<number>>(() => new Set());
  const [retryError, setRetryError] = useState<string | null>(null);

  useEffect(() => {
    const settled = links
      .filter((link) => link.pipeline_task_state === "failed" || link.pipeline_task_state === "completed")
      .map((link) => link.id);
    if (settled.length) {
      setQueued((current) => {
        const next = new Set(current);
        settled.forEach((id) => next.delete(id));
        return next;
      });
    }
  }, [links]);

  async function retry(linkId: number) {
    setRetrying((current) => new Set(current).add(linkId));
    setRetryError(null);
    try {
      await rerunLink(getAccessToken(), linkId);
      setQueued((current) => new Set(current).add(linkId));
    } catch {
      setRetryError(opsStrings.genericError);
    } finally {
      setRetrying((current) => {
        const next = new Set(current);
        next.delete(linkId);
        return next;
      });
    }
  }

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
      {retryError && <Typography role="alert">{retryError}</Typography>}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-right text-[13px]">
          <thead>
            <tr className="border-b border-[var(--ds-border)] text-muted">
              <th className="py-[8px] font-medium">URL</th>
              <th className="py-[8px] font-medium">{opsStrings.status}</th>
              <th className="py-[8px] font-medium">{opsStrings.reviewState}</th>
              <th className="py-[8px] font-medium">{opsStrings.qualityReviewTitle}</th>
              <th className="py-[8px] font-medium">{opsStrings.retry}</th>
            </tr>
          </thead>
          <tbody>
            {links.map((link) => (
              <tr className="border-b border-[var(--ds-border)]" key={link.id}>
                <td className="max-w-[420px] truncate py-[10px]" dir="ltr" title={link.url}>
                  {link.url}
                  {link.last_error && (
                    <span
                      className={`block text-[11px] ${link.last_error.startsWith("no_valid_plans:") ? "text-warning" : "text-danger"}`}
                      dir="rtl"
                    >
                      {link.last_error.startsWith("no_valid_plans:")
                        ? opsStrings.noValidPlansOutcome
                        : opsStrings.pipelineFailure}
                    </span>
                  )}
                </td>
                <td className="py-[10px]">
                  <StageBadge stage={link.pipeline_stage} />
                </td>
                <td className="py-[10px]">
                  {REVIEW_LABEL[link.review_state] ?? link.review_state}
                </td>
                <td className="py-[10px]">
                  {link.pipeline_stage === "plans_extracted" ? (
                    <NextLink
                      className="rounded-[var(--radius)] bg-accent px-[10px] py-[6px] text-[12px] font-medium text-accent-foreground"
                      href={`/ops/links/${link.id}/publish`}
                    >
                      {opsStrings.reviewPlans}
                    </NextLink>
                  ) : (
                    <span className="text-[12px] text-muted">{opsStrings.none}</span>
                  )}
                </td>
                <td className="py-[10px]">
                  <Button
                    isDisabled={
                      retrying.has(link.id) ||
                      link.pipeline_task_state === "queued" ||
                      link.pipeline_task_state === "running" ||
                      ["published", "flagged"].includes(link.pipeline_stage)
                    }
                    isPending={
                      retrying.has(link.id) ||
                      link.pipeline_task_state === "queued" ||
                      link.pipeline_task_state === "running"
                    }
                    onPress={() => retry(link.id)}
                    size="sm"
                    variant="secondary"
                  >
                    {link.pipeline_task_state === "queued" ||
                    link.pipeline_task_state === "running"
                      ? opsStrings.retryQueued
                      : opsStrings.retry}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
