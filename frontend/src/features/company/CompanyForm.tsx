"use client";

import { useState } from "react";

import { Body, Button, Card, CardTitle, Input } from "@/src/components/ui";
import { AuthApiError } from "@/src/lib/api/auth";
import { createCompany } from "@/src/lib/api/companies";
import { strings } from "@/src/lib/i18n/strings";
import { getAccessToken } from "@/src/lib/session";

/** Standalone company-information form (step one). Only this step's input is collected. */
export function CompanyForm({ onCreated }: { onCreated?: (id: number) => void }) {
  const [fields, setFields] = useState({
    domain: "",
    company_name: "",
    representative_name: "",
    phone_number: "",
    internal_number: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function update(key: keyof typeof fields, value: string) {
    setFields((prev) => ({ ...prev, [key]: value }));
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const token = getAccessToken();
    if (!token) {
      setError(strings.pleaseLogin);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await createCompany(token, fields);
      onCreated?.(result.company.id);
    } catch (err) {
      if (err instanceof AuthApiError) {
        const missing = (err.fields as { fields?: string[] }).fields;
        setError(missing?.length ? `${err.message} (${missing.join(", ")})` : err.message);
      } else {
        setError(strings.genericError);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card variant="featured" className="flex flex-col gap-[16px] p-[32px]">
      <CardTitle>{strings.registerNewCompany}</CardTitle>
      <form className="flex flex-col gap-[12px]" onSubmit={submit}>
        <label className="flex flex-col gap-[4px]">
          <Body>{strings.companyDomain}</Body>
          <Input
            name="domain"
            value={fields.domain}
            onChange={(e) => update("domain", e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-[4px]">
          <Body>{strings.companyName}</Body>
          <Input
            name="company_name"
            value={fields.company_name}
            onChange={(e) => update("company_name", e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-[4px]">
          <Body>{strings.representativeName}</Body>
          <Input
            name="representative_name"
            value={fields.representative_name}
            onChange={(e) => update("representative_name", e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-[4px]">
          <Body>{strings.companyPhone}</Body>
          <Input
            name="phone_number"
            value={fields.phone_number}
            onChange={(e) => update("phone_number", e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-[4px]">
          <Body>{strings.internalNumber}</Body>
          <Input
            name="internal_number"
            value={fields.internal_number}
            onChange={(e) => update("internal_number", e.target.value)}
          />
        </label>
        {error ? <Body className="text-[var(--ds-clay)]">{error}</Body> : null}
        <Button type="submit" variant="primary" disabled={busy}>
          {strings.submitCompany}
        </Button>
      </form>
    </Card>
  );
}
