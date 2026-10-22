import Link from "next/link";

import { strings } from "@/src/lib/i18n/strings";

/** Brand logotype; links home. Persian wordmark with the mono-style Latin app name. */
export function Logo({ className = "" }: { className?: string }) {
  return (
    <Link
      href="/"
      aria-label={strings.appName}
      className={`flex flex-row items-center gap-[8px] text-[var(--ds-ink)] ${className}`}
    >
      <span className="text-[20px] font-semibold">{strings.appName}</span>
      <span className="hidden font-mono text-[12px] font-medium uppercase text-[var(--ds-ink-muted)] sm:inline">
        {strings.brandTagline}
      </span>
    </Link>
  );
}
