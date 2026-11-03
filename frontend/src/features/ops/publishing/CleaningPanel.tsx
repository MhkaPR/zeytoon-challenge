"use client";

import { useTranslations } from "next-intl";
import { Button, Card, Chip, Separator, Typography } from "@heroui/react";
import { Broom, Send } from "lucide-react";

import type { CleaningResult, PublishResult } from "@/src/lib/api/ops";
import { StageBadge } from "../pipeline/StageBadge";

export function CleaningPanel({
  stage,
  recipeReady,
  cleaning,
  published,
  busy = false,
  onClean,
  onPublish,
}: {
  stage: string;
  recipeReady: boolean;
  cleaning: CleaningResult | null;
  published: PublishResult | null;
  busy?: boolean;
  onClean: () => void;
  onPublish: () => void;
}) {
  const ot = useTranslations();
  return (
    <div className="flex flex-col gap-[16px]">
      <StageBadge stage={published?.pipeline_stage ?? stage} />

      {!recipeReady && (
        <Typography className="text-[13px] text-warning" role="status">
          {ot("mapFirst")}
        </Typography>
      )}

      <div className="flex flex-wrap gap-[8px]">
        <Button isDisabled={busy || !recipeReady} onPress={onClean}>
          <Broom aria-hidden className="size-4" />
          {busy ? ot("cleaning") : ot("runCleaning")}
        </Button>
        <Button
          isDisabled={busy || !recipeReady || (!cleaning && !published)}
          onPress={onPublish}
          variant="secondary"
        >
          <Send aria-hidden className="size-4" />
          {busy ? ot("publishing") : ot("runPublish")}
        </Button>
      </div>

      {cleaning && (
        <Card className="flex flex-col gap-[10px] p-[18px]" variant="default">
          <div className="flex flex-wrap items-center gap-[8px]">
            <Chip color="success" size="sm" variant="soft">
              {ot("cleanedRecords")}: {cleaning.cleaned_records}
            </Chip>
            <Chip
              color={cleaning.exception_count > 0 ? "warning" : "default"}
              size="sm"
              variant="soft"
            >
              {ot("exceptionCount")}: {cleaning.exception_count}
            </Chip>
          </div>

          <Typography className="text-[13px] font-semibold" type="h3">
            {ot("exceptions")}
          </Typography>
          {cleaning.exception_count === 0 ? (
            <Typography className="text-[12px] text-success">
              {ot("noExceptions")}
            </Typography>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-right text-[12px]">
                <thead>
                  <tr className="border-b border-[var(--ds-border)] text-muted">
                    <th className="py-[6px] font-medium">{ot("naturalKey")}</th>
                    <th className="py-[6px] font-medium">{ot("exceptions")}</th>
                  </tr>
                </thead>
                <tbody>
                  {cleaning.records
                    .filter((record) => Object.keys(record.exceptions).length > 0)
                    .map((record) => (
                      <tr
                        className="border-b border-[var(--ds-border)]"
                        key={record.natural_key}
                      >
                        <td className="py-[8px]" dir="ltr">
                          {record.natural_key}
                        </td>
                        <td className="py-[8px]">
                          {Object.entries(record.exceptions)
                            .map(([field, message]) => `${field}: ${message}`)
                            .join("، ")}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {published && (
        <Card className="flex flex-col gap-[8px] p-[18px]" variant="secondary">
          <Chip color="success" size="sm" variant="soft">
            {ot("publishedCount")}: {published.published}
          </Chip>
          <Typography className="text-[13px] font-semibold" type="h3">
            {ot("provenance")}
          </Typography>
          <Typography className="text-[12px] text-muted">
            {ot("provenanceHint")}
          </Typography>
          <Separator />
          <Typography className="text-[12px] text-muted">
            {ot("exceptionCount")}: {published.exception_count}
          </Typography>
        </Card>
      )}
    </div>
  );
}
