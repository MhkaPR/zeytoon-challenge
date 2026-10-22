"use client";

import { Button, Card, Input, Label, TextField, Typography } from "@heroui/react";
import { useState } from "react";

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
    <Card className="p-[32px]" variant="tertiary">
      <Card.Header>
        <Card.Title>{strings.registerNewCompany}</Card.Title>
      </Card.Header>
      <Card.Content className="mt-[16px]">
      <form className="flex flex-col gap-[16px]" onSubmit={submit}>
        <TextField name="domain" value={fields.domain} onChange={(v) => update("domain", v)}>
          <Label>{strings.companyDomain}</Label>
          <Input />
        </TextField>
        <TextField
          name="company_name"
          value={fields.company_name}
          onChange={(v) => update("company_name", v)}
        >
          <Label>{strings.companyName}</Label>
          <Input />
        </TextField>
        <TextField
          name="representative_name"
          value={fields.representative_name}
          onChange={(v) => update("representative_name", v)}
        >
          <Label>{strings.representativeName}</Label>
          <Input />
        </TextField>
        <TextField
          name="phone_number"
          value={fields.phone_number}
          onChange={(v) => update("phone_number", v)}
        >
          <Label>{strings.companyPhone}</Label>
          <Input />
        </TextField>
        <TextField
          name="internal_number"
          value={fields.internal_number}
          onChange={(v) => update("internal_number", v)}
        >
          <Label>{strings.internalNumber}</Label>
          <Input />
        </TextField>
        {error ? (
          <Typography className="text-danger" role="alert">
            {error}
          </Typography>
        ) : null}
        <Button className="self-start" isDisabled={busy} type="submit">
          {strings.submitCompany}
        </Button>
      </form>
      </Card.Content>
    </Card>
  );
}
