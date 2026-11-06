"use client";

import { Button, Modal, Typography } from "@heroui/react";
import NextLink from "next/link";
import { useTranslations } from "next-intl";

import { ensureHttps, type PublicPlan } from "@/src/lib/api/publicCatalog";

import { formatPrice, numberValue, priceOf } from "../planCatalogUtils";

const HIDDEN_FIELDS = new Set(["plan_name", "name"]);
const OTHER_FIELD = "other";
const AMOUNT_UNITS: Record<string, string> = {
  ram_amount: "ram_unit",
  storage_amount: "storage_unit",
  disk_amount: "disk_unit",
  traffic_amount: "traffic_unit",
  bandwidth_amount: "bandwidth_unit",
};

type OtherAttribute = { label: string; value: string };

function readableValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return String(value);
  }
  if (Array.isArray(value)) {
    return value
      .map((item) => readableValue(item))
      .filter(Boolean)
      .join("، ");
  }
  if (typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .filter(([, item]) => item !== null && item !== undefined && item !== "")
      .map(([key, item]) => `${key.replaceAll("_", " ")}: ${readableValue(item)}`)
      .filter(Boolean)
      .join("، ");
  }
  return String(value);
}

function normalizeOtherAttributes(value: unknown): OtherAttribute[] {
  if (value === null || value === undefined || value === "") return [];
  const entries = Array.isArray(value) ? value : [value];

  return entries.flatMap((entry) => {
    if (entry === null || entry === undefined || entry === "") return [];

    if (typeof entry === "object" && !Array.isArray(entry)) {
      const record = entry as Record<string, unknown>;
      const rawLabel = record.label ?? record.name ?? record.key ?? record.title;
      const hasValue = "value" in record || "text" in record || "answer" in record;

      if (rawLabel !== undefined && hasValue) {
        const label = readableValue(rawLabel);
        const attributeValue = readableValue(
          record.value ?? record.text ?? record.answer,
        );
        return label && attributeValue ? [{ label, value: attributeValue }] : [];
      }

      return Object.entries(record)
        .filter(([, item]) => item !== null && item !== undefined && item !== "")
        .map(([key, item]) => ({
          label: key.replaceAll("_", " "),
          value: readableValue(item),
        }))
        .filter((attribute) => attribute.value);
    }

    const scalar = readableValue(entry);
    return scalar ? [{ label: "", value: scalar }] : [];
  });
}

function detailValue(
  key: string,
  value: unknown,
  values: PublicPlan["values"],
): string {
  if (key === "price_amount" || key === "price") {
    return formatPrice(numberValue(value));
  }
  const unitKey = AMOUNT_UNITS[key];
  if (unitKey && values[unitKey] != null && values[unitKey] !== "") {
    return `${String(value)} ${String(values[unitKey])}`;
  }
  return String(value);
}

export function PlanDetailsModal({
  plan,
  isOpen,
  onOpenChange,
}: {
  plan: PublicPlan;
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
}) {
  const ot = useTranslations();
  const fieldLabels = ot.raw("fieldLabels") as Record<string, string>;
  const price = priceOf(plan);
  const details = [
    ["plan_type", plan.plan_type] as const,
    ...Object.entries(plan.values).filter(
      ([key, value]) =>
        !HIDDEN_FIELDS.has(key) &&
        key !== OTHER_FIELD &&
        value !== null &&
        value !== undefined &&
        value !== "",
    ),
  ];
  const otherAttributes = normalizeOtherAttributes(plan.values[OTHER_FIELD]);

  return (
    <Modal isOpen={isOpen} onOpenChange={onOpenChange}>
      <Modal.Backdrop>
        <Modal.Container size="lg">
          <Modal.Dialog
            aria-label={ot("planDetailsTitle")}
            className="w-full sm:max-w-[560px]"
          >
            <Modal.CloseTrigger />
            <Modal.Header>
              <Modal.Heading className="text-[22px] font-semibold">
                {String(plan.values.plan_name ?? plan.values.name ?? plan.plan_type)}
              </Modal.Heading>
              <Typography color="muted" type="body-sm">
                {plan.company_name} · {plan.domain}
              </Typography>
            </Modal.Header>
            <Modal.Body className="flex flex-col gap-[18px]">
              <div className="rounded-[var(--radius)] bg-surface-secondary p-[14px]">
                <Typography className="text-[11px] text-muted" type="body-xs">
                  {ot("planDetailsPrice")}
                </Typography>
                <Typography className="text-[20px] font-semibold" type="body">
                  {price ? `${formatPrice(price)} ${ot("pricePerMonth")}` : ot("priceUnknown")}
                </Typography>
              </div>

              <dl className="grid grid-cols-1 gap-x-[16px] gap-y-[12px] sm:grid-cols-2">
                {details.map(([key, value]) => (
                  <div className="flex flex-col gap-[3px]" key={key}>
                    <dt className="text-[11px] text-muted">
                      {fieldLabels[key] ?? key.replaceAll("_", " ")}
                    </dt>
                    <dd className="text-[13px]">{detailValue(key, value, plan.values)}</dd>
                  </div>
                ))}
              </dl>

              {otherAttributes.length > 0 ? (
                <section
                  aria-labelledby="plan-other-attributes"
                  className="flex flex-col gap-[10px]"
                >
                  <h3
                    className="text-[13px] font-semibold"
                    id="plan-other-attributes"
                  >
                    {ot("otherAttributes")}
                  </h3>
                  <dl className="grid grid-cols-1 gap-x-[16px] gap-y-[10px] rounded-[var(--radius)] bg-surface-secondary p-[14px] sm:grid-cols-2">
                    {otherAttributes.map((attribute, index) => (
                      <div
                        className="flex flex-col gap-[3px]"
                        key={`${attribute.label}-${index}`}
                      >
                        {attribute.label ? (
                          <dt className="text-[11px] text-muted">
                            {attribute.label}
                          </dt>
                        ) : null}
                        <dd className="text-[13px]">{attribute.value}</dd>
                      </div>
                    ))}
                  </dl>
                </section>
              ) : null}
            </Modal.Body>
            <Modal.Footer>
              <NextLink
                className="flex-1"
                href={`/companies/${encodeURIComponent(plan.domain)}`}
              >
                <Button className="w-full" variant="secondary">
                  {ot("viewCompany")}
                </Button>
              </NextLink>
              <a
                className="flex-1"
                href={ensureHttps(plan.url ?? plan.domain)}
                rel="noopener noreferrer"
                target="_blank"
              >
                <Button className="w-full" variant="primary">
                  {ot("viewPlanPage")}
                </Button>
              </a>
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}
