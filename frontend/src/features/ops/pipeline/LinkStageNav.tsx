"use client";

import NextLink from "next/link";

import { opsStrings } from "@/src/lib/i18n/strings";

const STAGES = [
  { key: "capture", label: opsStrings.openCapture },
  { key: "tables", label: opsStrings.openTables },
  { key: "mapping", label: opsStrings.openMapping },
  { key: "publish", label: opsStrings.openPublishing },
] as const;

/** Reachable stage switcher for one link, so every console screen has a path in the UI. */
export function LinkStageNav({ linkId, active }: { linkId: number; active: string }) {
  return (
    <nav aria-label={opsStrings.console}>
      <ul className="flex flex-wrap gap-[6px]">
        {STAGES.map((stage) => {
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
  );
}
