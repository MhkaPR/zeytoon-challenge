"use client";

import { Chip } from "@heroui/react";

import { useTranslations } from "next-intl";

const COLORS: Record<string, "default" | "success" | "warning" | "danger" | "accent"> = {
  review: "default",
  capture: "warning",
  extracted: "accent",
  mapped: "accent",
  cleaned: "success",
  published: "success",
  no_plans: "warning",
  flagged: "danger",
  failed: "danger",
};

export function StageBadge({ stage }: { stage: string }) {
  const ot = useTranslations();
  const stageLabels: Record<string, string> = {
    review: ot("stageReview"), capture: ot("stageCapture"), extracted: ot("stageExtracted"),
    mapped: ot("stageMapped"), cleaned: ot("stageCleaned"), published: ot("stagePublished"),
    no_plans: ot("stageNoPlans"), flagged: ot("stageFlagged"), failed: ot("stageFailed"),
  };
  return (
    <Chip color={COLORS[stage] ?? "default"} size="sm" variant="soft">
      {stageLabels[stage] ?? stage}
    </Chip>
  );
}
