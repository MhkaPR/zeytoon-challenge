"use client";

import { Chip } from "@heroui/react";
import { Building2, Check } from "lucide-react";
import NextLink from "next/link";
import { buttonVariants } from "@heroui/react";

import type { SwitcherEntry } from "@/src/lib/api/companies";
import { strings } from "@/src/lib/i18n/strings";

import { verificationColor, verificationLabel } from "./status";

export function CompanySwitcher({
  companies,
  activeId,
}: {
  companies: SwitcherEntry[];
  activeId?: number;
}) {
  if (companies.length === 0) return null;

  return (
    <nav aria-label={strings.switchCompany} className="w-full">
      <ul className="flex flex-col gap-[12px] sm:-mx-1 sm:flex-row sm:snap-x sm:snap-mandatory sm:overflow-x-auto sm:px-[4px] sm:pb-[4px]">
        {companies.map((entry) => {
          const active = entry.id === activeId;

          return (
            <li key={entry.id} className="sm:snap-start">
              <NextLink
                href={`/panel/${entry.id}`}
                aria-current={active ? "page" : undefined}
                className={buttonVariants({
                  variant: "secondary",
                  className:
                    "flex h-auto w-full flex-col items-stretch justify-start gap-[10px] p-[16px] text-left sm:w-[220px]",
                })}
              >
                <div className="flex items-center gap-[8px]">
                  <span
                    aria-hidden
                    className={`flex size-[32px] shrink-0 items-center justify-center rounded-full ${
                      active
                        ? "bg-accent text-accent-foreground"
                        : "bg-surface-secondary text-muted"
                    }`}
                  >
                    {active ? (
                      <Check className="size-4" />
                    ) : (
                      <Building2 className="size-4" />
                    )}
                  </span>
                  <span className="truncate text-[15px] font-semibold">
                    {entry.company_name}
                  </span>
                </div>

                <Chip
                  color={verificationColor(entry.verification_status)}
                  size="sm"
                  variant="soft"
                >
                  {verificationLabel(entry.verification_status)}
                </Chip>
              </NextLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}