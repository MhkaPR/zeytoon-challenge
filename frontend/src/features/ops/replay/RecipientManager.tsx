"use client";

import { useTranslations } from "next-intl";
import { Button, Card, Chip, Input, Label, TextField, Typography } from "@heroui/react";
import { useState } from "react";

import type { Recipient } from "@/src/lib/api/ops";
export function RecipientManager({
  recipients,
  busy = false,
  onAdd,
  onDeactivate,
}: {
  recipients: Recipient[];
  busy?: boolean;
  onAdd: (userId: number, name: string) => void;
  onDeactivate: (recipientId: number) => void;
}) {
  const ot = useTranslations("ops");
  const [userId, setUserId] = useState("");
  const [name, setName] = useState("");

  return (
    <Card className="flex flex-col gap-[12px] p-[18px]" variant="secondary">
      <Typography className="text-[16px] font-semibold" type="h3">
        {ot("recipientsTitle")}
      </Typography>
      <Typography className="text-[12px] text-muted">{ot("inAppOnly")}</Typography>

      <div className="grid gap-[8px] sm:grid-cols-2">
        <TextField name="recipient-user" value={userId} onChange={setUserId}>
          <Label>{ot("recipientUserId")}</Label>
          <Input inputMode="numeric" />
        </TextField>
        <TextField name="recipient-name" value={name} onChange={setName}>
          <Label>{ot("recipientName")}</Label>
          <Input />
        </TextField>
      </div>
      <Button
        className="self-start"
        isDisabled={busy || !userId.trim()}
        onPress={() => {
          onAdd(Number(userId), name);
          setUserId("");
          setName("");
        }}
        size="sm"
      >
        {ot("addRecipient")}
      </Button>

      {recipients.length === 0 ? (
        <Typography className="text-[12px] text-muted">
          {ot("noRecipients")}
        </Typography>
      ) : (
        <ul className="flex flex-col gap-[8px]">
          {recipients.map((recipient) => (
            <li
              className="flex flex-wrap items-center justify-between gap-[8px] border-b border-[var(--ds-border)] py-[8px]"
              key={recipient.id}
            >
              <div className="flex flex-col gap-[2px]">
                <span className="text-[13px] font-medium">
                  {recipient.name || `#${recipient.user_id}`}
                </span>
                <span className="text-[11px] text-muted" dir="ltr">
                  {ot("userPhone")}: {recipient.user_phone}
                </span>
              </div>
              <div className="flex items-center gap-[6px]">
                <Chip
                  color={recipient.is_active ? "success" : "default"}
                  size="sm"
                  variant="soft"
                >
                  {recipient.is_active ? ot("active") : ot("inactive")}
                </Chip>
                <Button
                  isDisabled={busy || !recipient.is_active}
                  onPress={() => onDeactivate(recipient.id)}
                  size="sm"
                  variant="ghost"
                >
                  {ot("deactivate")}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
