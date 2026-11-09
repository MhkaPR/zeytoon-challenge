import type { VerificationStatus } from "@/src/lib/api/companies";

export type ChipColor = "default" | "accent" | "success" | "warning" | "danger";

/** Message key for a company verification status. */
export function verificationLabelKey(status: VerificationStatus): string {
  if (status === "verified") return "verifiedStatus";
  if (status === "rejected") return "rejectedStatus";
  return "pendingStatus";
}

/** Chip color for a company verification status (DESIGN.md §2.2 role-bound hues). */
export function verificationColor(status: VerificationStatus): ChipColor {
  if (status === "verified") return "success";
  if (status === "rejected") return "danger";
  return "warning";
}
