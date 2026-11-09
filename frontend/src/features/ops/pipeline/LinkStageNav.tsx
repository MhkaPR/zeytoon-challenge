"use client";

import { useTranslations } from "next-intl";
import { buttonVariants } from "@heroui/react";
import { ArrowRight, Map, Send, Table2, Video } from "lucide-react";
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
    { key: "capture", label: ot("openCapture"), icon: Video },
    { key: "tables", label: ot("openTables"), icon: Table2 },
    { key: "mapping", label: ot("openMapping"), icon: Map },
    { key: "publish", label: ot("openPublishing"), icon: Send },
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
            const Icon = stage.icon;
            return (
              <li key={stage.key}>
                <NextLink
                  aria-current={isActive ? "page" : undefined}
                  className={buttonVariants({
                    size: "sm",
                    variant: isActive ? "primary" : "secondary",
                  })}
                  href={`/ops/links/${linkId}/${stage.key}`}
                >
                  <Icon aria-hidden className="size-4" />
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
