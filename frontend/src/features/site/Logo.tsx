import { useTranslations } from "next-intl";
import NextLink from "next/link";

/** Brand logotype; links home. Persian wordmark with the mono-style Latin app name. */
export function Logo({ className = "" }: { className?: string }) {
  const t = useTranslations("common");
  return (
    <NextLink
      href="/"
      aria-label={t("appName")}
      className={`flex flex-row items-center gap-[8px] text-foreground ${className}`}
    >
      <span className="text-[20px] font-semibold">{t("appName")}</span>
    </NextLink>
  );
}
