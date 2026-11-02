import type { VerificationStatus } from "@/src/lib/api/companies";
import { strings } from "@/src/lib/i18n/strings";

export type ChipColor = "default" | "accent" | "success" | "warning" | "danger";

/** Persian label for a company verification status. */
export function verificationLabel(status: VerificationStatus): string {
  if (status === "verified") return strings.verifiedStatus;
  if (status === "rejected") return strings.rejectedStatus;
  return strings.pendingStatus;
}

/** Chip color for a company verification status (DESIGN.md §2.2 role-bound hues). */
export function verificationColor(status: VerificationStatus): ChipColor {
  if (status === "verified") return "success";
  if (status === "rejected") return "danger";
  return "warning";
}

/** Persian label for a company charge status. */
export function chargeLabel(charged: boolean): string {
  return charged ? strings.chargedStatus : strings.notChargedStatus;
}

/** Chip color for a company charge status. */
export function chargeColor(charged: boolean): ChipColor {
  return charged ? "success" : "warning";
}
