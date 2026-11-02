"use client";

import { useTranslations } from "next-intl";
import { Button, Card, Chip, Separator, TextArea, Typography } from "@heroui/react";
import { Building2, Globe, Phone, User } from "lucide-react";
import { useState } from "react";

import { addCompanyLinks, type Company } from "@/src/lib/api/companies";
import { getAccessToken } from "@/src/lib/session";

import { PlanEligibilityNotice } from "./PlanEligibilityNotice";
import { verificationColor, verificationLabel } from "./status";

// Company panel: identity, verification, plan eligibility and domain link submission.

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
  const t = useTranslations("common");
  const [urlsText, setUrlsText] = useState("");
  const [linksBusy, setLinksBusy] = useState(false);
  const [linksMessage, setLinksMessage] = useState("");

  async function submitLinks() {
    const token = getAccessToken();
    if (!token) return;
    const urls = urlsText.split(/\r?\n/).map((url) => url.trim()).filter(Boolean);
    if (!urls.length) return;
    setLinksBusy(true);
    setLinksMessage("");
    try {
      const result = await addCompanyLinks(token, company.id, urls);
      setUrlsText("");
      setLinksMessage(`${result.links.length} لینک ثبت شد.`);
    } catch {
      setLinksMessage(t("genericError"));
    } finally {
      setLinksBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-[24px]">
      <Card className="flex flex-col gap-[20px] p-[24px] sm:p-[32px]" variant="default">
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
          </div>
        </div>

        <Separator />

        <div className="flex flex-col">
          <InfoRow
            icon={<User className="size-4" />}
            label={t("representativeName")}
            value={company.representative_name}
          />
          <InfoRow
            icon={<Phone className="size-4" />}
            label={t("companyPhone")}
            ltr
            value={
              company.internal_number
                ? `${company.phone_number} — ${company.internal_number}`
                : company.phone_number
            }
          />
        </div>
      </Card>

      <Card className="flex flex-col gap-[20px] p-[24px] sm:p-[32px]" variant="default">
        <div className="flex flex-col gap-[4px]">
          <Typography className="text-[18px] font-semibold" type="h2">
            {t("plansGateTitle")}
          </Typography>
          <Typography className="text-[13px] leading-[1.8]" color="muted">
            {t("panelPermissionsHint")}
          </Typography>
        </div>
        <PlanEligibilityNotice companyId={company.id} />
      </Card>

      <Card className="flex flex-col gap-[16px] p-[24px] sm:p-[32px]" variant="default">
        <div className="flex flex-col gap-[4px]">
          <Typography className="text-[18px] font-semibold" type="h2">افزودن لینک‌های سرویس</Typography>
          <Typography className="text-[13px] leading-[1.8]" color="muted">هر آدرس را در یک خط وارد کنید. فقط لینک‌های دامنهٔ شرکت پذیرفته می‌شوند.</Typography>
        </div>
        <TextArea aria-label="لینک‌های سرویس" value={urlsText} onChange={(event) => setUrlsText(event.target.value)} placeholder="https://example.com/plans" rows={5} />
        <div className="flex items-center gap-[12px]">
          <Button isDisabled={linksBusy} onPress={submitLinks}>{linksBusy ? "در حال ثبت…" : "ثبت لینک‌ها"}</Button>
          {linksMessage && <Typography role="status" type="body-sm">{linksMessage}</Typography>}
        </div>
      </Card>
    </div>
  );
}
