"use client";

import { Button, Card, Typography } from "@heroui/react";

import { strings } from "@/src/lib/i18n/strings";

/** Empty state shown when the user owns no companies (FR-023). */
export function EmptyState({ onRegister }: { onRegister?: () => void }) {
  return (
    <Card className="flex flex-col items-start gap-[16px] p-[32px]" variant="tertiary">
      <Card.Title>{strings.companyPanel}</Card.Title>
      <Typography className="text-muted">{strings.noCompanies}</Typography>
      <Button onPress={onRegister}>{strings.registerNewCompany}</Button>
    </Card>
  );
}
