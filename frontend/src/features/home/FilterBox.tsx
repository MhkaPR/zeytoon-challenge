"use client";

import { Select } from "@/src/components/ui";
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

  return (
    <div className="flex flex-col gap-[16px] rounded-[var(--radius-comfortable)] bg-[var(--ds-white)] p-[16px] shadow-[var(--ds-shadow-subtle)] md:flex-row md:flex-wrap md:items-start">
      <Select
        label={strings.serverLocationLabel}
        placeholder={strings.anyOption}
        options={SERVER_LOCATIONS[serviceType].map((location) => ({
          value: location,
          label: location,
        }))}
        value={value.location}
        onChange={(event) => onChange({ ...value, location: event.target.value })}
      />

      {resourceKeys.map((key) => (
        <Select
          key={key}
          label={RESOURCE_LABELS[key]}
          placeholder={strings.anyOption}
          options={RESOURCE_OPTIONS[key].map((amount) => ({
            value: String(amount),
            label: String(amount),
          }))}
          value={value.resources[key] ?? ""}
          onChange={(event) =>
            onChange({
              ...value,
              resources: { ...value.resources, [key]: event.target.value },
            })
          }
        />
      ))}

      <PriceRangeBox
        value={value.price}
        onChange={(price) => onChange({ ...value, price })}
      />
    </div>
  );
}
