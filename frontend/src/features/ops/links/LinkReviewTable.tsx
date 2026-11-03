"use client";

import { useTranslations } from "next-intl";
import { Button, Typography } from "@heroui/react";
import NextLink from "next/link";
import { useMemo, useState } from "react";

import type { Link } from "@/src/lib/api/ops";
import { StageBadge } from "../pipeline/StageBadge";

export function LinkReviewTable({
  links,
  busy = false,
  onReview,
}: {
  links: Link[];
  busy?: boolean;
  onReview: (keepIds: number[], removeIds: number[]) => void;
}) {
  const ot = useTranslations();
  const [removed, setRemoved] = useState<Set<number>>(
    () => new Set(links.filter((link) => link.review_state === "removed").map((link) => link.id)),
  );

  const kept = useMemo(
    () => links.filter((link) => !removed.has(link.id)),
    [links, removed],
  );

  function toggle(linkId: number) {
    setRemoved((previous) => {
      const next = new Set(previous);
      if (next.has(linkId)) next.delete(linkId);
      else next.add(linkId);
      return next;
    });
  }

  if (links.length === 0) {
    return (
      <Typography className="text-[13px] text-warning" role="status">
        {ot("linksEmpty")}
      </Typography>
    );
  }

  return (
    <div className="flex flex-col gap-[12px]">
      <div className="flex flex-wrap items-center gap-[12px] text-[12px] text-muted">
        <span>
          {ot("keptCount")}: {kept.length}
        </span>
        <span>
          {ot("removedCount")}: {removed.size}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-right text-[13px]">
          <thead>
            <tr className="border-b border-[var(--ds-border)] text-muted">
              <th className="py-[8px] font-medium">URL</th>
              <th className="py-[8px] font-medium">{ot("status")}</th>
              <th className="py-[8px] font-medium">{ot("keep")}</th>
              <th className="py-[8px] font-medium">{ot("action")}</th>
            </tr>
          </thead>
          <tbody>
            {links.map((link) => {
              const isRemoved = removed.has(link.id);
              return (
                <tr className="border-b border-[var(--ds-border)]" key={link.id}>
                  <td className="max-w-[420px] truncate py-[10px]" dir="ltr" title={link.url}>
                    {link.url}
                  </td>
                  <td className="py-[10px]">
                    <StageBadge stage={link.pipeline_stage} />
                  </td>
                  <td className="py-[10px]">
                    <Button
                      aria-pressed={!isRemoved}
                      isDisabled={busy}
                      onPress={() => toggle(link.id)}
                      size="sm"
                      variant={isRemoved ? "secondary" : "ghost"}
                    >
                      {isRemoved ? ot("restore") : ot("remove")}
                    </Button>
                  </td>
                  <td className="py-[10px]">
                    {link.review_state === "kept" && !isRemoved ? (
                      <NextLink
                        className="rounded-[var(--radius)] bg-accent px-[10px] py-[6px] text-[12px] font-medium text-accent-foreground"
                        href={`/ops/links/${link.id}/capture`}
                      >
                        {ot("openCapture")}
                      </NextLink>
                    ) : (
                      <span className="text-[12px] text-muted">{ot("none")}</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <Button
        className="self-start"
        isDisabled={busy}
        onPress={() =>
          onReview(
            kept.map((link) => link.id),
            Array.from(removed),
          )
        }
      >
        {busy ? ot("reviewing") : ot("reviewSubmit")}
      </Button>
    </div>
  );
}
