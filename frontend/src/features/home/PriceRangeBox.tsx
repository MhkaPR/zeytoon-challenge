"use client";

import { useTranslations } from "next-intl";
import {
  Button,
  Description,
  Label,
  NumberField,
  Popover,
  Typography,
} from "@heroui/react";
import { useState } from "react";

import { strings } from "@/src/lib/i18n/strings";
export interface PriceRange {
  from: string;
  to: string;
}

const EMPTY_PRICE: PriceRange = { from: "", to: "" };

/** Human-readable summary of the active range, or the "any price" placeholder. */
function summarize(value: PriceRange): string {
  if (!value.from && !value.to) return strings.priceAny;
  const from = value.from ? Number(value.from).toLocaleString("fa-IR") : "۰";
  const to = value.to ? Number(value.to).toLocaleString("fa-IR") : "∞";
  return `${from} – ${to}`;
}

/**
 * Price-range filter: a HeroUI ``Popover`` whose trigger shows the active range and whose
 * dialog holds two ``NumberField`` inputs (from/to) with apply/clear actions (PAGES.yaml
 * "price range box"). ``draft`` holds the in-dialog values so the filter only changes on
 * Apply.
 */
export function PriceRangeBox({
  value,
  onChange,
}: {
  value: PriceRange;
  onChange: (next: PriceRange) => void;
}) {
  const t = useTranslations("common");
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<PriceRange>(value);
  const active = Boolean(value.from || value.to);

  function handleOpenChange(next: boolean) {
    // Reset the draft to the committed value whenever the dialog opens.
    if (next) setDraft(value);
    setOpen(next);
  }

  function apply() {
    onChange(draft);
    setOpen(false);
  }

  function clear() {
    setDraft(EMPTY_PRICE);
    onChange(EMPTY_PRICE);
    setOpen(false);
  }

  return (
    <div className="flex w-full flex-col gap-[6px] sm:w-[200px]">
      <Typography className="px-[2px]" type="body-xs" color="muted">
        {t("priceRangeLabel")}
      </Typography>
      <Popover isOpen={open} onOpenChange={handleOpenChange}>
        <Button
          aria-label={t("priceRangeLabel")}
          className="w-full justify-between"
          variant={active ? "primary" : "secondary"}
        >
          <span className="truncate">{summarize(value)}</span>
          <span aria-hidden className="shrink-0 text-[10px]">
            {open ? "▲" : "▼"}
          </span>
        </Button>
        <Popover.Content className="w-[300px]" placement="bottom end">
          <Popover.Dialog
            aria-label={t("priceRangeLabel")}
            className="flex flex-col gap-[16px]"
          >
            <Popover.Heading>{t("priceRangeLabel")}</Popover.Heading>
          <div className="flex flex-row items-end gap-[8px]">
            <NumberField
              className="flex-1"
              minValue={0}
              name="priceFrom"
              value={draft.from === "" ? undefined : Number(draft.from)}
              onChange={(next) => setDraft((prev) => ({ ...prev, from: Number.isNaN(next) ? "" : String(next) }))}
            >
              <Label>{t("priceFrom")}</Label>
              <NumberField.Group>
                <NumberField.DecrementButton />
                <NumberField.Input className="w-full" inputMode="numeric" />
                <NumberField.IncrementButton />
              </NumberField.Group>
            </NumberField>
            <NumberField
              className="flex-1"
              minValue={0}
              name="priceTo"
              value={draft.to === "" ? undefined : Number(draft.to)}
              onChange={(next) => setDraft((prev) => ({ ...prev, to: Number.isNaN(next) ? "" : String(next) }))}
            >
              <Label>{t("priceTo")}</Label>
              <NumberField.Group>
                <NumberField.DecrementButton />
                <NumberField.Input className="w-full" inputMode="numeric" />
                <NumberField.IncrementButton />
              </NumberField.Group>
            </NumberField>
          </div>
          <Description className="flex flex-col gap-[4px]">
            <Typography type="body-xs" color="muted">
              {summarize(draft)}
            </Typography>
          </Description>
          <div className="flex flex-row justify-end gap-[8px]">
            <Button onPress={clear} size="sm" variant="ghost">
              {t("priceRangeClear")}
            </Button>
            <Button onPress={apply} size="sm">
              {t("priceRangeApply")}
            </Button>
          </div>
        </Popover.Dialog>
      </Popover.Content>
      </Popover>
    </div>
  );
}
