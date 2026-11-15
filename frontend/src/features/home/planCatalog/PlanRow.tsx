"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRef } from "react";

import type { PublicPlan } from "@/src/lib/api/publicCatalog";

import { PlanCard } from "./PlanCard";

/** Horizontally scrollable plan row with hidden scrollbar and explicit controls. */
export function PlanRow({
  plans,
  visitorId,
  ariaLabel,
}: {
  plans: PublicPlan[];
  visitorId?: string;
  ariaLabel: string;
}) {
  const ot = useTranslations();
  const listRef = useRef<HTMLUListElement>(null);

  const move = (direction: -1 | 1) => {
    listRef.current?.scrollBy({
      left: direction * 320,
      behavior: "smooth",
    });
  };

  return (
    <div className="flex flex-col gap-[8px]">
      <ul
        aria-label={ariaLabel}
        className="-mx-[24px] flex snap-x snap-mandatory gap-[16px] overflow-x-auto px-[24px] pb-[6px] sm:mx-0 sm:px-0 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        ref={listRef}
      >
        {plans.map((plan) => (
          <li className="shrink-0 snap-start list-none" key={plan.id}>
            <PlanCard plan={plan} visitorId={visitorId} />
          </li>
        ))}
      </ul>
      <div className="flex justify-end gap-[8px]">
        <button
          aria-label={ot("previousPage")}
          className="flex size-[34px] items-center justify-center rounded-full border border-[var(--separator)] bg-surface text-foreground transition hover:bg-surface-secondary"
          type="button"
          onClick={() => move(1)}
        >
          <ChevronRight aria-hidden className="size-4" />
        </button>
        <button
          aria-label={ot("nextPage")}
          className="flex size-[34px] items-center justify-center rounded-full border border-[var(--separator)] bg-surface text-foreground transition hover:bg-surface-secondary"
          type="button"
          onClick={() => move(-1)}
        >
          <ChevronLeft aria-hidden className="size-4" />
        </button>
      </div>
    </div>
  );
}
