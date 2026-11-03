"use client";

import { useTranslations } from "next-intl";
import {
  Button,
  Card,
  Input,
  Label,
  Switch,
  TextField,
  Typography,
  TextArea,
} from "@heroui/react";
import { useState } from "react";

const NUMBER_FIELDS = [
  { key: "REPLAY_PERIOD_HOURS", labelKey: "replayPeriod" },
  { key: "FAILURE_RATE_THRESHOLD", labelKey: "failureThreshold" },
  { key: "FAILURE_RATE_WINDOW_RUNS", labelKey: "failureWindow" },
  { key: "CATALOG_PRICE_MIN", labelKey: "catalogPriceMin" },
  { key: "CATALOG_PRICE_MAX", labelKey: "catalogPriceMax" },
  { key: "CATALOG_PRICE_STEP", labelKey: "catalogPriceStep" },
  { key: "CATALOG_PAGE_SIZE_DEFAULT", labelKey: "catalogPageSizeDefault" },
  {
    key: "CATALOG_COMPANY_FILTER_VISIBLE",
    labelKey: "catalogCompanyFilterVisible",
  },
  { key: "OPS_SITE_REFRESH_MS", labelKey: "opsSiteRefreshMs" },
  { key: "OPS_LINKS_REFRESH_MS", labelKey: "opsLinksRefreshMs" },
  { key: "CAPTURE_FIXED_DURATION_MS", labelKey: "captureFixedDurationMs" },
] as const;

const TEXT_FIELDS = [
  { key: "CONTACT_EMAIL", labelKey: "contactEmail" },
  { key: "CONTACT_PHONE", labelKey: "contactPhone" },
  { key: "CONTACT_ADDRESS", labelKey: "contactAddress" },
  { key: "SOCIAL_INSTAGRAM_URL", labelKey: "socialInstagramUrl" },
  { key: "SOCIAL_TELEGRAM_URL", labelKey: "socialTelegramUrl" },
  { key: "SOCIAL_LINKEDIN_URL", labelKey: "socialLinkedinUrl" },
  { key: "SOCIAL_GITHUB_URL", labelKey: "socialGithubUrl" },
] as const;

const JSON_FIELDS = [
  { key: "CATALOG_PAGE_SIZES", labelKey: "catalogPageSizes" },
  { key: "CATALOG_RESOURCE_OPTIONS", labelKey: "catalogResourceOptions" },
] as const;

export function TunablesForm({
  values,
  busy = false,
  onSave,
}: {
  values: Record<string, unknown>;
  busy?: boolean;
  onSave: (values: Record<string, unknown>) => void;
}) {
  const ot = useTranslations();
  const [draft, setDraft] = useState<Record<string, unknown>>(() => ({ ...values }));
  const [parseError, setParseError] = useState<string | null>(null);

  function update(key: string, value: unknown) {
    setDraft((previous) => ({ ...previous, [key]: value }));
  }

  return (
    <Card className="flex flex-col gap-[16px] p-[20px]" variant="default">
      <Typography className="text-[16px] font-semibold" type="h3">
        {ot("settingsTitle")}
      </Typography>
      <Typography className="text-[12px] text-muted">{ot("settingsIntro")}</Typography>

      {NUMBER_FIELDS.map((field) => (
        <TextField
          key={field.key}
          name={field.key}
          value={String(draft[field.key] ?? "")}
          onChange={(value) => update(field.key, Number(value))}
        >
          <Label>{ot(field.labelKey)}</Label>
          <Input inputMode="decimal" />
        </TextField>
      ))}

      {TEXT_FIELDS.map((field) => (
        <TextField
          key={field.key}
          name={field.key}
          value={String(draft[field.key] ?? "")}
          onChange={(value) => update(field.key, value)}
        >
          <Label>{ot(field.labelKey)}</Label>
          <Input />
        </TextField>
      ))}

      {JSON_FIELDS.map((field) => (
        <TextField
          key={field.key}
          name={field.key}
          value={
            typeof draft[field.key] === "string"
              ? String(draft[field.key])
              : JSON.stringify(draft[field.key] ?? null, null, 2)
          }
          onChange={(value) => update(field.key, value)}
        >
          <Label>{ot(field.labelKey)}</Label>
          <TextArea rows={4} />
        </TextField>
      ))}

      <Switch
        isSelected={Boolean(draft.LABELING_ENABLED)}
        onChange={(selected) => update("LABELING_ENABLED", selected)}
      >
        <Switch.Content>
          <Switch.Control>
            <Switch.Thumb />
          </Switch.Control>
          {ot("labelingEnabled")}
        </Switch.Content>
      </Switch>

      <TextField
        name="CLEANING_RULES"
        value={
          typeof draft.CLEANING_RULES === "string"
            ? draft.CLEANING_RULES
            : JSON.stringify(draft.CLEANING_RULES ?? {}, null, 2)
        }
        onChange={(value) => update("CLEANING_RULES", value)}
      >
        <Label>{ot("cleaningRules")}</Label>
        <TextArea rows={4} />
      </TextField>

      {parseError && (
        <Typography className="text-[12px] text-danger" role="alert">
          {parseError}
        </Typography>
      )}

      <Button
        className="self-start"
        isDisabled={busy}
        onPress={() => {
          const payload: Record<string, unknown> = { ...draft };
          for (const field of JSON_FIELDS) {
            if (typeof payload[field.key] !== "string") continue;
            try {
              payload[field.key] = JSON.parse(String(payload[field.key]));
            } catch {
              setParseError(ot(field.labelKey));
              return;
            }
          }
          if (typeof payload.CLEANING_RULES === "string") {
            try {
              payload.CLEANING_RULES = JSON.parse(payload.CLEANING_RULES);
            } catch {
              setParseError(ot("cleaningRules"));
              return;
            }
          }
          setParseError(null);
          onSave(payload);
        }}
      >
        {busy ? ot("saving") : ot("saveSettings")}
      </Button>
    </Card>
  );
}
