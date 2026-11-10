"use client";

import {Button, Card, Typography} from "@heroui/react";
import { Building2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import {ensureHttps, PublicPlan} from "@/src/lib/api/publicCatalog";
import { sendSignal } from "@/src/lib/api/signals";
import type { Reason } from "@/src/lib/api/explanations";
import { fieldValue, formatPrice, priceOf } from "../planCatalogUtils";
import { PlanDetailsModal } from "./PlanDetailsModal";
import { WhyRecommended } from "./WhyRecommended";

/** Company icon with a neutral local fallback when the domain has no favicon. */
function CompanyFavicon({ domain }: { domain: string }) {
  const [hasError, setHasError] = useState(false);

  if (hasError) {
    return (
      <span aria-hidden="true" className="flex size-[32px] shrink-0 items-center justify-center rounded-[8px] border border-[var(--separator)] text-muted">
        <Building2 className="size-[16px]" />
      </span>
    );
  }

  return (
    <img
      alt=""
      aria-hidden="true"
      className="size-[32px] shrink-0 rounded-[8px] border border-[var(--separator)] bg-background object-contain p-[4px]"
      height={32}
      loading="lazy"
      onError={() => setHasError(true)}
      src={`https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=64`}
      width={32}
    />
  );
}

/** One published service plan. Plan name is the primary heading; provider is secondary. */
export function PlanCard({
  plan,
  explanation,
  visitorId,
}: {
  plan: PublicPlan;
  explanation?: Reason[];
  visitorId?: string;
}) {
  const ot = useTranslations();
  const [detailsOpen, setDetailsOpen] = useState(false);
  const price = priceOf(plan);
  const cpu = plan.values.vcpu_cores ?? plan.values.cpu_cores ?? plan.values.cpu;
  const ram = plan.values.ram_amount ?? plan.values.ram;
  const disk = plan.values.storage_amount ?? plan.values.disk_amount ?? plan.values.disk;
  const location = fieldValue(plan, ["location", "datacenter_location"]);

  return (
    <Card className="relative h-full border border-[var(--separator)] shadow-none" variant="default">
      <Card.Content className="flex h-full flex-col gap-[16px] p-[18px]">
        <div className="flex items-start justify-between gap-[16px]">
          <div className="flex min-w-0 flex-col gap-[5px]">
            <Typography className="text-[17px] font-semibold leading-[1.6]" type="h3">
              {String(plan.values.plan_name ?? plan.values.name ?? plan.plan_type)}
            </Typography>
            <div className="flex items-center gap-[8px]">
              <CompanyFavicon domain={plan.domain} />
              <div className="min-w-0">
                <Typography className="truncate text-[12px] font-medium" type="body-sm">
                  {plan.company_name}
                </Typography>
                <Typography className="truncate text-[11px]" color="muted" type="body-xs">
                  {plan.domain}
                </Typography>
              </div>
            </div>
          </div>
          <div className="shrink-0 text-end">
            {price ? (
              <>
                <Typography className="text-[15px] font-semibold" type="body-sm">{formatPrice(price)}</Typography>
                <Typography className="text-[10px]" color="muted" type="body-xs">{ot("pricePerMonth")}</Typography>
              </>
            ) : <Typography color="muted" type="body-sm">{ot("priceUnknown")}</Typography>}
          </div>
        </div>

        <dl className="grid grid-cols-2 gap-x-[12px] gap-y-[10px] border-t border-[var(--separator)] pt-[14px] text-[11px]">
          <div className="flex flex-col gap-[3px]">
            <dt className="text-muted">{ot("resourceCpu")}</dt>
            <dd>{cpu == null ? "—" : `${String(cpu)} vCPU`}</dd>
          </div>
          <div className="flex flex-col gap-[3px]">
            <dt className="text-muted">{ot("specRam")}</dt>
            <dd>{ram == null ? "—" : `${String(ram)} ${String(plan.values.ram_unit ?? "GB")}`}</dd>
          </div>
          <div className="flex flex-col gap-[3px]">
            <dt className="text-muted">{ot("resourceDisk")}</dt>
            <dd>{disk == null ? "—" : `${String(disk)} ${String(plan.values.storage_unit ?? plan.values.disk_unit ?? "GB")}`}</dd>
          </div>
          <div className="flex flex-col gap-[3px]">
            <dt className="text-muted">{ot("topHostsLocationLabel")}</dt>
            <dd>{location == null ? "—" : String(location)}</dd>
          </div>
        </dl>
        {explanation?.length ? <WhyRecommended reasons={explanation} /> : null}
        <div className="flex justify-center gap-2 w-full">
        <Button
          className="w-full"
          variant="secondary"
          onPress={() => {
            sendSignal("details_view", [plan.id], undefined, visitorId);
            setDetailsOpen(true);
          }}
        >
          {ot("viewPlanDetails")}
        </Button>
        <a
          target="_blank"
          rel="noopener noreferrer"
          className="w-full flex justify-start mt-auto text-[12px] font-medium text-accent"
          href={ensureHttps(plan.url ?? plan.domain)}
        >
          <Button
            className="w-full"
            variant="primary"
            onPress={() =>
              sendSignal("destination_visit", [plan.id], undefined, visitorId)
            }
          >
            {ot("viewPlanPage")}
          </Button>
        </a>
        </div>
      </Card.Content>
      <PlanDetailsModal
        isOpen={detailsOpen}
        onOpenChange={setDetailsOpen}
        plan={plan}
      />
    </Card>
  );
}

