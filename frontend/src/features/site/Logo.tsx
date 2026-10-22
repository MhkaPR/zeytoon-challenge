import NextLink from "next/link";

import { strings } from "@/src/lib/i18n/strings";

/** Brand logotype; links home. Persian wordmark with the mono-style Latin app name. */
export function Logo({ className = "" }: { className?: string }) {
  return (
    <NextLink
      href="/"
      aria-label={strings.appName}
      className={`flex flex-row items-center gap-[8px] text-foreground ${className}`}
    >
      <span className="text-[20px] font-semibold">{strings.appName}</span>
      <span className="hidden font-mono text-[12px] font-medium uppercase text-muted sm:inline">
        {strings.brandTagline}
      </span>
    </NextLink>
  );
}
