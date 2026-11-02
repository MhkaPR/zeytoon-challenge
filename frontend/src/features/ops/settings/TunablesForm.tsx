"use client";

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

import { opsStrings } from "@/src/lib/i18n/strings";

const NUMBER_FIELDS = [
  { key: "REPLAY_PERIOD_HOURS", label: opsStrings.replayPeriod },
  { key: "FAILURE_RATE_THRESHOLD", label: opsStrings.failureThreshold },
  { key: "FAILURE_RATE_WINDOW_RUNS", label: opsStrings.failureWindow },
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
  const [draft, setDraft] = useState<Record<string, unknown>>(() => ({ ...values }));
  const [parseError, setParseError] = useState<string | null>(null);

  function update(key: string, value: unknown) {
    setDraft((previous) => ({ ...previous, [key]: value }));
  }

  return (
    <Card className="flex flex-col gap-[16px] p-[20px]" variant="default">
      <Typography className="text-[16px] font-semibold" type="h3">
        {opsStrings.settingsTitle}
      </Typography>
      <Typography className="text-[12px] text-muted">{opsStrings.settingsIntro}</Typography>

      {NUMBER_FIELDS.map((field) => (
        <TextField
          key={field.key}
          name={field.key}
          value={String(draft[field.key] ?? "")}
          onChange={(value) => update(field.key, Number(value))}
        >
          <Label>{field.label}</Label>
          <Input inputMode="decimal" />
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
          {opsStrings.labelingEnabled}
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
        <Label>{opsStrings.cleaningRules}</Label>
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
          if (typeof payload.CLEANING_RULES === "string") {
            try {
              payload.CLEANING_RULES = JSON.parse(payload.CLEANING_RULES);
            } catch {
              setParseError(opsStrings.cleaningRules);
              return;
            }
          }
          setParseError(null);
          onSave(payload);
        }}
      >
        {busy ? opsStrings.saving : opsStrings.saveSettings}
      </Button>
    </Card>
  );
}
