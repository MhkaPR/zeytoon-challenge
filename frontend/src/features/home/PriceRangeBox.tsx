"use client";

import { useState } from "react";

import { Body, Button, Input, MonoLabel } from "@/src/components/ui";
import { strings } from "@/src/lib/i18n/strings";

export interface PriceRange {
  from: string;
  to: string;
}

/**
 * A combo-style control: collapsed it shows the current price range; clicking it opens a
 * from/to range field so the user can filter their needed price range (PAGES.yaml
 * "price range box").
 */
export function PriceRangeBox({
  value,
  onChange,
}: {
  value: PriceRange;
  onChange: (next: PriceRange) => void;
}) {
  const [open, setOpen] = useState(false);
  const summary =
    value.from || value.to
      ? `${value.from || "۰"} - ${value.to || "∞"}`
      : strings.anyOption;

  return (
    <div className="flex flex-col gap-[6px]">
      <MonoLabel>{strings.priceRangeLabel}</MonoLabel>
      <Button
        variant="secondary"
        aria-label={strings.priceRangeLabel}
        aria-expanded={open}
        onClick={() => setOpen((previous) => !previous)}
        className="justify-between"
      >
        <Body as="span" tone="muted">
          {summary}
        </Body>
        <span aria-hidden>{open ? "▲" : "▼"}</span>
      </Button>
      {open && (
        <div className="flex flex-row items-end gap-[8px]">
          <Input
            type="number"
            inputMode="numeric"
            label={strings.priceFrom}
            min={0}
            value={value.from}
            onChange={(event) => onChange({ ...value, from: event.target.value })}
          />
          <Input
            type="number"
            inputMode="numeric"
            label={strings.priceTo}
            min={0}
            value={value.to}
            onChange={(event) => onChange({ ...value, to: event.target.value })}
          />
        </div>
      )}
    </div>
  );
}
