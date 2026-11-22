const PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹";

/** Formats numbers identically in Node and browsers without relying on ICU locale data. */
export function formatPersianNumber(value: number): string {
  if (!Number.isFinite(value)) return String(value);
  const [integer, fraction] = String(value).split(".");
  const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, "٬");
  return `${grouped}${fraction === undefined ? "" : `٫${fraction}`}`.replace(/\d/g, (digit) => PERSIAN_DIGITS[Number(digit)]);
}

/** Formats an ISO timestamp as a Tehran calendar date with Persian digits. */
export function formatTehranDate(isoTimestamp: string): string {
  const date = new Date(isoTimestamp);
  if (Number.isNaN(date.getTime())) return "";
  const tehranDate = new Date(date.getTime() + 210 * 60_000);
  return `${formatPersianNumber(tehranDate.getUTCMonth() + 1)}/${formatPersianNumber(tehranDate.getUTCDate())}`;
}
