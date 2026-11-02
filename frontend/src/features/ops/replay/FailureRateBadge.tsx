"use client";

import { Chip } from "@heroui/react";

import { opsStrings } from "@/src/lib/i18n/strings";

export function FailureRateBadge({
  rate,
  threshold,
}: {
  rate: number;
  threshold: number;
}) {
  const exceeded = rate >= threshold;
  return (
    <Chip color={exceeded ? "danger" : "success"} size="sm" variant="soft">
      {opsStrings.failureRate}: {(rate * 100).toFixed(1)}% / {opsStrings.threshold}:{" "}
      {(threshold * 100).toFixed(1)}%
    </Chip>
  );
}
