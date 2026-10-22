"use client";

import { Button, Label, ListBox, Select, Surface, Typography } from "@heroui/react";

import { strings } from "@/src/lib/i18n/strings";
import { PriceRangeBox, type PriceRange } from "./PriceRangeBox";
import {
  RESOURCE_LABELS,
  RESOURCE_OPTIONS,
  SERVER_LOCATIONS,
  resourcesForType,
  type ServiceTypeKey,
} from "./serviceTypes";

export interface FilterState {
  location: string;
  resources: Record<string, string>;
  price: PriceRange;
}

export const EMPTY_FILTERS: FilterState = {
  location: "",
  resources: {},
  price: { from: "", to: "" },
};

/** A labelled single-select HeroUI ``Select`` bound to a plain string value. */
export function FilterSelect({
  label,
  options,
  value,
  onChange,
  className = "",
}: {
  label: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (next: string) => void;
  className?: string;
}) {
  return (
    <Select
      aria-label={label}
      className={className}
      placeholder={strings.anyOption}
      value={value || null}
      onChange={(key) => onChange(key == null ? "" : String(key))}
    >
      <Label className="px-[2px]">{label}</Label>
      <Select.Trigger>
        <Select.Value />
        <Select.Indicator />
      </Select.Trigger>
      <Select.Popover>
        <ListBox>
          {options.map((option) => (
            <ListBox.Item id={option.value} key={option.value} textValue={option.label}>
              {option.label}
              <ListBox.ItemIndicator />
            </ListBox.Item>
          ))}
        </ListBox>
      </Select.Popover>
    </Select>
  );
}

function hasActiveFilters(value: FilterState): boolean {
  return Boolean(value.location || value.price.from || value.price.to) ||
    Object.values(value.resources).some(Boolean);
}

/**
 * Immediate-filter panel below the chips: a server-location combo (dynamic per service
 * type), small-to-big resource choosers (host/servers only; CDN gets traffic alone), and a
 * price range box (PAGES.yaml "filter box").
 */
export function FilterBox({
  serviceType,
  value,
  onChange,
}: {
  serviceType: ServiceTypeKey;
  value: FilterState;
  onChange: (next: FilterState) => void;
}) {
  const resourceKeys = resourcesForType(serviceType);
  const active = hasActiveFilters(value);

  return (
    <Surface
      className="flex flex-col gap-[16px] rounded-[var(--radius)] p-[20px] shadow-surface"
      variant="secondary"
    >
      <div className="flex flex-row items-center justify-between gap-[8px]">
        <Typography className="font-semibold" type="body-sm">
          {strings.filtersTitle}
        </Typography>
        {active && (
          <Button onPress={() => onChange(EMPTY_FILTERS)} size="sm" variant="ghost">
            {strings.clearFilters}
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 gap-[16px] sm:grid-cols-2 lg:grid-cols-4">
        <FilterSelect
          className="w-full"
          label={strings.serverLocationLabel}
          options={SERVER_LOCATIONS[serviceType].map((location) => ({
            value: location,
            label: location,
          }))}
          value={value.location}
          onChange={(next) => onChange({ ...value, location: next })}
        />

        {resourceKeys.map((key) => (
          <FilterSelect
            key={key}
            className="w-full"
            label={RESOURCE_LABELS[key]}
            options={RESOURCE_OPTIONS[key].map((amount) => ({
              value: String(amount),
              label: String(amount),
            }))}
            value={value.resources[key] ?? ""}
            onChange={(next) =>
              onChange({ ...value, resources: { ...value.resources, [key]: next } })
            }
          />
        ))}

        <PriceRangeBox value={value.price} onChange={(price) => onChange({ ...value, price })} />
      </div>
    </Surface>
  );
}
