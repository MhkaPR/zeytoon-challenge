import type { PublicPlan } from "@/src/lib/api/publicCatalog";

export const formatPrice = (value: number) => value.toLocaleString("fa-IR");

export function numberValue(value: unknown): number {
  if (typeof value === "number") return value;
  if (typeof value === "string") return Number(value.replaceAll(",", "")) || 0;
  return 0;
}

export function fieldValue(plan: PublicPlan, keys: string[]): unknown {
  for (const key of keys) {
    const value = plan.values[key];
    if (value !== null && value !== undefined && value !== "") return value;
  }
  return undefined;
}

export function priceOf(plan: PublicPlan): number {
  return numberValue(plan.values.price_amount ?? plan.values.price);
}
