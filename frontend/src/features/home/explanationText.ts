import type { Reason } from "@/src/lib/api/explanations";

type Translate = {
  raw: (key: string) => unknown;
};

function template(t: Translate, key: string): string {
  const value = t.raw(key);
  return typeof value === "string" ? value : key;
}

function interpolate(source: string, values: Record<string, string>): string {
  return Object.entries(values).reduce(
    (text, [key, value]) => text.replaceAll(`{${key}}`, value),
    source,
  );
}

function formatNumber(value: number): string {
  return value.toLocaleString("fa-IR", { maximumFractionDigits: 1 });
}

const NUMERIC_KEYS: Record<string, string> = {
  cpu: "explainNumericCpu",
  ram: "explainNumericRam",
  disk: "explainNumericDisk",
  traffic: "explainNumericTraffic",
  price: "explainNumericPrice",
};

const CATEGORICAL_KEYS: Record<string, string> = {
  os: "explainCategoricalOs",
  country: "explainCategoricalCountry",
};

/** Build one localized reason sentence from a single feature reason. */
export function reasonSentence(reason: Reason, t: Translate): string {
  if (reason.type === "textual") {
    return template(t, "explainTextual");
  }
  if (reason.type === "categorical") {
    const key = CATEGORICAL_KEYS[reason.feature] ?? "explainCategorical";
    return interpolate(template(t, key), { value: reason.label ?? "" });
  }
  const key = NUMERIC_KEYS[reason.feature];
  if (!key || !reason.real_range) {
    return "";
  }
  const [low, high] = reason.real_range;
  return interpolate(template(t, key), {
    low: formatNumber(low),
    high: formatNumber(high),
  });
}

/** One localized sentence per reason, skipping any that cannot be rendered. */
export function reasonSentences(reasons: Reason[], t: Translate): string[] {
  return reasons.map((reason) => reasonSentence(reason, t)).filter(Boolean);
}

/** Join the reasons into one localized explanation. */
export function explanationText(reasons: Reason[], t: Translate): string {
  return reasonSentences(reasons, t).join("\n");
}
