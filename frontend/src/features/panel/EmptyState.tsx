"use client";

import { Body, Button, Card, CardTitle } from "@/src/components/ui";
import { strings } from "@/src/lib/i18n/strings";

/** Empty state shown when the user owns no companies (FR-023). */
export function EmptyState({ onRegister }: { onRegister?: () => void }) {
  return (
    <Card variant="featured" className="flex flex-col items-start gap-[16px] p-[32px]">
      <CardTitle>{strings.companyPanel}</CardTitle>
      <Body className="text-[var(--ds-text-muted)]">
        {strings.noCompanies}
      </Body>
      <Button variant="primary" onClick={onRegister}>
        {strings.registerNewCompany}
      </Button>
    </Card>
  );
}
