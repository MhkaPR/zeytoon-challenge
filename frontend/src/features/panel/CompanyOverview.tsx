"use client";

import { Card, Chip, Separator, Switch, Typography } from "@heroui/react";
import { Building2, Globe, Phone, User } from "lucide-react";
import { useState } from "react";

import { setCrawlEnabled, type Company } from "@/src/lib/api/companies";
import { strings } from "@/src/lib/i18n/strings";
import { getAccessToken } from "@/src/lib/session";

import { PlanEligibilityNotice } from "./PlanEligibilityNotice";
import { chargeColor, chargeLabel, verificationColor, verificationLabel } from "./status";

// Full company panel for a verified company: identity, verification and charge status, the
// crawl switch, and the plan-eligibility gate (FR-024, FR-030, FR-031, FR-035).

function InfoRow({
  icon,
  label,
  value,
  ltr,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  ltr?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-[16px] py-[10px]">
      <span className="flex items-center gap-[8px] text-[13px] text-muted">
        <span aria-hidden className="text-muted">
          {icon}
        </span>
        {label}
      </span>
      <span className="text-[14px] font-medium" dir={ltr ? "ltr" : undefined}>
        {value || "—"}
      </span>
    </div>
  );
}

export function CompanyOverview({ company }: { company: Company }) {
  const charged = company.charge_status === "charged";
  const [crawlEnabled, setCrawl] = useState(company.crawl_enabled);
  const [crawlBusy, setCrawlBusy] = useState(false);
  const [crawlError, setCrawlError] = useState(false);

  async function toggleCrawl(next: boolean) {
    const token = getAccessToken();
    if (!token) return;
    setCrawlBusy(true);
    setCrawlError(false);
    try {
      const result = await setCrawlEnabled(token, company.id, next);
      setCrawl(result.crawl_enabled);
    } catch {
      setCrawlError(true);
    } finally {
      setCrawlBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-[24px]">
      <Card className="flex flex-col gap-[20px] p-[24px] sm:p-[32px]" variant="secondary">
        <div className="flex flex-wrap items-start justify-between gap-[16px]">
          <div className="flex items-center gap-[12px]">
            <span
              aria-hidden
              className="flex size-[48px] shrink-0 items-center justify-center rounded-[var(--radius)] bg-accent-soft text-accent"
            >
              <Building2 className="size-6" />
            </span>
            <div className="flex flex-col gap-[4px]">
              <Typography className="text-[20px] font-semibold" type="h2">
                {company.company_name}
              </Typography>
              <span className="flex items-center gap-[6px] text-[13px] text-muted" dir="ltr">
                <Globe className="size-4 shrink-0" />
                {company.domain}
              </span>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-[8px]">
            <Chip color={verificationColor(company.verification_status)} variant="soft">
              {verificationLabel(company.verification_status)}
            </Chip>
            <Chip color={chargeColor(charged)} variant="soft">
              {chargeLabel(charged)}
            </Chip>
          </div>
        </div>

        <Separator />

        <div className="flex flex-col">
          <InfoRow
            icon={<User className="size-4" />}
            label={strings.representativeName}
            value={company.representative_name}
          />
          <InfoRow
            icon={<Phone className="size-4" />}
            label={strings.companyPhone}
            ltr
            value={
              company.internal_number
                ? `${company.phone_number} — ${company.internal_number}`
                : company.phone_number
            }
          />
        </div>
      </Card>

      <Card className="flex flex-col gap-[20px] p-[24px] sm:p-[32px]" variant="secondary">
        <div className="flex flex-col gap-[4px]">
          <Typography className="text-[18px] font-semibold" type="h2">
            {strings.plansGateTitle}
          </Typography>
          <Typography className="text-[13px] leading-[1.8]" color="muted">
            {strings.panelPermissionsHint}
          </Typography>
        </div>
        <PlanEligibilityNotice companyId={company.id} />
      </Card>

      <Card className="flex flex-col gap-[20px] p-[24px] sm:p-[32px]" variant="secondary">
        <div className="flex flex-wrap items-center justify-between gap-[16px]">
          <div className="flex flex-col gap-[4px]">
            <Typography className="text-[18px] font-semibold" type="h2">
              {strings.crawlTitle}
            </Typography>
            <Typography className="text-[13px] leading-[1.8]" color="muted">
              {strings.crawlHint}
            </Typography>
          </div>
          <Switch
            isDisabled={crawlBusy || !charged}
            isSelected={crawlEnabled}
            onChange={toggleCrawl}
          >
            <Switch.Content>
              <Switch.Control>
                <Switch.Thumb />
              </Switch.Control>
              {crawlEnabled ? strings.crawlEnabledStatus : strings.crawlDisabledStatus}
            </Switch.Content>
          </Switch>
        </div>
        {crawlError && (
          <Typography className="text-[13px] text-danger" role="alert">
            {strings.genericError}
          </Typography>
        )}
      </Card>
    </div>
  );
}
