"use client";

import {
  Button,
  Card,
  Input,
  Label,
  ListBox,
  Select,
  TextField,
  Typography,
} from "@heroui/react";
import { useState } from "react";

import { opsStrings } from "@/src/lib/i18n/strings";

export function LlmCeilingForm({
  ceiling,
  period,
  spend,
  exceeded,
  busy = false,
  onSave,
}: {
  ceiling: number | null;
  period: string;
  spend: number;
  exceeded: boolean;
  busy?: boolean;
  onSave: (amount: number | null, period: string) => void;
}) {
  const [amount, setAmount] = useState(ceiling === null ? "" : String(ceiling));
  const [selectedPeriod, setSelectedPeriod] = useState(period || "monthly");

  return (
    <Card className="flex flex-col gap-[16px] p-[20px]" variant="secondary">
      <Typography className="text-[16px] font-semibold" type="h3">
        {opsStrings.ceilingTitle}
      </Typography>

      <div className="flex flex-wrap gap-[8px] text-[12px]">
        <span className="text-muted">
          {opsStrings.spend}: {spend.toFixed(2)}
        </span>
        <span className={exceeded ? "text-danger" : "text-success"}>
          {exceeded ? opsStrings.ceilingExceeded : opsStrings.ceilingOk}
        </span>
      </div>

      <TextField name="ceiling" value={amount} onChange={setAmount}>
        <Label>{opsStrings.ceilingAmount}</Label>
        <Input inputMode="decimal" />
      </TextField>

      <Select
        className="w-full"
        selectedKey={selectedPeriod}
        onSelectionChange={(key) => {
          if (typeof key === "string") setSelectedPeriod(key);
        }}
      >
        <Label>{opsStrings.ceilingPeriod}</Label>
        <Select.Trigger>
          <Select.Value />
          <Select.Indicator />
        </Select.Trigger>
        <Select.Popover>
          <ListBox>
            <ListBox.Item id="monthly" textValue={opsStrings.monthly}>
              {opsStrings.monthly}
              <ListBox.ItemIndicator />
            </ListBox.Item>
            <ListBox.Item id="daily" textValue={opsStrings.daily}>
              {opsStrings.daily}
              <ListBox.ItemIndicator />
            </ListBox.Item>
          </ListBox>
        </Select.Popover>
      </Select>

      <Button
        className="self-start"
        isDisabled={busy}
        onPress={() =>
          onSave(amount.trim() === "" ? null : Number(amount), selectedPeriod)
        }
        variant="secondary"
      >
        {busy ? opsStrings.saving : opsStrings.saveCeiling}
      </Button>
    </Card>
  );
}
