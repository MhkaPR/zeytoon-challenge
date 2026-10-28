"use client";

import { Chip } from "@heroui/react";

import { stageLabels } from "@/src/lib/i18n/strings";

const COLORS: Record<string, "default" | "success" | "warning" | "danger" | "accent"> = {
  review: "default",
  capture: "warning",
  extracted: "accent",
  mapped: "accent",
  cleaned: "success",
  published: "success",
  flagged: "danger",
  failed: "danger",
};

export function StageBadge({ stage }: { stage: string }) {
  return (
    <Chip color={COLORS[stage] ?? "default"} size="sm" variant="soft">
      {stageLabels[stage] ?? stage}
    </Chip>
  );
}
