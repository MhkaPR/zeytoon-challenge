"use client";

import { useTranslations } from "next-intl";
import { ArrowRight } from "lucide-react";
import NextLink from "next/link";


/** Reachable stage switcher for one link, so every console screen has a path in the UI. */
export function LinkStageNav({
  linkId,
  active,
  siteId,
}: {
  linkId: number;
  active: string;
  siteId?: number | null;
}) {
  const ot = useTranslations();
  const stages = [
    { key: "capture", label: ot("openCapture") }, { key: "tables", label: ot("openTables") },
    { key: "mapping", label: ot("openMapping") }, { key: "publish", label: ot("openPublishing") },
  ] as const;
  return (
    <div className="flex flex-col gap-[8px]">
      {siteId != null && (
        <NextLink
          className="flex w-fit items-center gap-[6px] text-[13px] font-medium text-muted hover:text-foreground"
          href={`/ops/sites/${siteId}/links`}
        >
          <ArrowRight aria-hidden className="size-4" />
          {ot("backToLinks")}
        </NextLink>
      )}
      <nav aria-label={ot("console")}>
        <ul className="flex flex-wrap gap-[6px]">
          {stages.map((stage) => {
            const isActive = stage.key === active;
            return (
              <li key={stage.key}>
                <NextLink
                  aria-current={isActive ? "page" : undefined}
                  className={`rounded-[var(--radius)] px-[10px] py-[6px] text-[13px] font-medium ${
                    isActive
                      ? "bg-accent text-accent-foreground"
                      : "bg-surface-secondary text-muted hover:text-foreground"
                  }`}
                  href={`/ops/links/${linkId}/${stage.key}`}
                >
                  {stage.label}
                </NextLink>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}
