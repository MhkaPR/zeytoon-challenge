"use client";

import { Button, Card, Chip, Input, Label, Separator, TextField, Typography } from "@heroui/react";
import { AlertTriangle, Building2, Globe, Phone, User } from "lucide-react";
import { useState } from "react";

import type { ApprovalQueueEntry } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";

function Info({ label, value, ltr }: { label: string; value: string; ltr?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-[12px]">
      <span className="text-[12px] text-muted">{label}</span>
      <span className="text-[14px] font-medium" dir={ltr ? "ltr" : undefined}>
        {value || opsStrings.none}
      </span>
    </div>
  );
}

export function CompanyReviewCard({
  entry,
  busy = false,
  onDecision,
}: {
  entry: ApprovalQueueEntry;
  busy?: boolean;
  onDecision: (companyId: number, outcome: "approved" | "not_approved", note: string) => void;
}) {
  const [note, setNote] = useState("");

  return (
    <Card className="flex flex-col gap-[16px] p-[20px]" variant="default">
      <div className="flex flex-wrap items-start justify-between gap-[12px]">
        <div className="flex items-center gap-[10px]">
          <span className="flex size-[40px] items-center justify-center rounded-full bg-accent-soft text-accent">
            <Building2 aria-hidden className="size-5" />
          </span>
          <div className="flex flex-col gap-[2px]">
            <Typography className="text-[17px] font-semibold" type="h3">
              {entry.company_name}
            </Typography>
            <span className="text-[12px] text-muted" dir="ltr">
              {entry.domain}
            </span>
          </div>
        </div>
        {entry.duplicate_domain_warning && (
          <Chip color="warning" size="sm" variant="soft">
            <AlertTriangle aria-hidden className="size-3" />
            {opsStrings.duplicateWarning}
          </Chip>
        )}
      </div>

      {entry.duplicate_domain_warning && (
        <Typography className="text-[13px] text-warning" role="status">
          {opsStrings.duplicateOf}: {entry.duplicate_of.join("، ") || opsStrings.none}
        </Typography>
      )}

      <Separator />

      <div className="grid gap-[8px] sm:grid-cols-2">
        <div className="flex flex-col gap-[8px]">
          <span className="flex items-center gap-[6px] text-[13px] text-muted">
            <User aria-hidden className="size-3.5" />
            {opsStrings.representative}
          </span>
          <span className="text-[14px] font-medium">{entry.representative_name}</span>
          <span className="flex items-center gap-[6px] text-[13px] text-muted">
            <Globe aria-hidden className="size-3.5" />
            {opsStrings.domain}
          </span>
          <span className="text-[14px] font-medium" dir="ltr">
            {entry.domain}
          </span>
        </div>
        <div className="flex flex-col gap-[8px]">
          <span className="flex items-center gap-[6px] text-[13px] text-muted">
            <Phone aria-hidden className="size-3.5" />
            {opsStrings.phone}
          </span>
          <span className="text-[14px] font-medium" dir="ltr">
            {entry.phone_masked}
          </span>
          <Info label={opsStrings.registeredAt} value={entry.registered_at} />
        </div>
      </div>

      <TextField name={`note-${entry.company_id}`} value={note} onChange={setNote}>
        <Label>{opsStrings.decisionNote}</Label>
        <Input placeholder={opsStrings.decisionNotePlaceholder} />
      </TextField>

      <div className="flex flex-wrap gap-[8px]">
        <Button isDisabled={busy} onPress={() => onDecision(entry.company_id, "approved", note)}>
          {busy ? opsStrings.deciding : opsStrings.approve}
        </Button>
        <Button
          isDisabled={busy}
          onPress={() => onDecision(entry.company_id, "not_approved", note)}
          variant="danger"
        >
          {opsStrings.reject}
        </Button>
      </div>
    </Card>
  );
}
