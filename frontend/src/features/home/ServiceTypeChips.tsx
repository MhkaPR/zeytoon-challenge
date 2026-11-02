"use client";

import { useTranslations } from "next-intl";
import { ToggleButton, ToggleButtonGroup, Typography } from "@heroui/react";
import { useState } from "react";

import { SERVICE_TYPES, type ServiceTypeKey } from "./serviceTypes";

/**
 * A horizontal row of service-type chips that filter results fast. Exactly one chip is
 * active at a time; the active chip drives which resources the filter box shows
 * (PAGES.yaml "chips").
 */
export function ServiceTypeChips() {
  const t = useTranslations("common");
  const [value, setValue] = useState<ServiceTypeKey>("host");
  return (
    <div className="flex flex-col gap-[8px]">
      <Typography type="body-xs" color="muted">
        {t("serviceTypeLabel")}
      </Typography>
      <ToggleButtonGroup
        aria-label={t("serviceTypeLabel")}
        className="flex-wrap"
        isDetached
        selectedKeys={[value]}
        selectionMode="single"
        onSelectionChange={(keys) => {
          const next = [...keys][0];
          if (typeof next === "string") setValue(next as ServiceTypeKey);
        }}
      >
        {SERVICE_TYPES.map((type) => (
          <ToggleButton className="rounded-full" id={type.key} key={type.key}>
            {type.label}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
    </div>
  );
}
