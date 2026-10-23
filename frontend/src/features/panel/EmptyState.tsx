"use client";

import { Button, Card, Typography } from "@heroui/react";
import { Building2 } from "lucide-react";

import { strings } from "@/src/lib/i18n/strings";

/** Empty state shown when the user owns no companies (FR-023). */
export function EmptyState({ onRegister }: { onRegister?: () => void }) {
  return (
    <Card className="items-center gap-[20px] p-[40px] text-center" variant="default">
      <span
        aria-hidden
        className="flex size-[56px] items-center justify-center rounded-full bg-accent-soft text-accent"
      >
        <Building2 className="size-6" />
      </span>
      <div className="flex flex-col gap-[8px]">
        <Typography className="text-[20px] font-semibold" type="h2">
          {strings.panelEmptyTitle}
        </Typography>
        <Typography className="max-w-[440px] leading-[1.8]" color="muted">
          {strings.panelEmptyBody}
        </Typography>
      </div>
      <Button onPress={onRegister}>{strings.registerNewCompany}</Button>
    </Card>
  );
}
