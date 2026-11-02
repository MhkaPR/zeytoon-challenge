"use client";

import { useTranslations } from "next-intl";
import { Chip } from "@heroui/react";

export function FailureRateBadge({
  rate,
  threshold,
}: {
  rate: number;
  threshold: number;
}) {
  const ot = useTranslations("ops");
  const exceeded = rate >= threshold;
  return (
    <Chip color={exceeded ? "danger" : "success"} size="sm" variant="soft">
      {ot("failureRate")}: {(rate * 100).toFixed(1)}% / {ot("threshold")}:{" "}
      {(threshold * 100).toFixed(1)}%
    </Chip>
  );
}
