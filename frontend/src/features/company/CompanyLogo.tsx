"use client";

import { useState } from "react";

/** Company favicon with a neutral vector fallback. */
export function CompanyLogo({
  domain,
  name,
  size = 44,
}: {
  domain?: string;
  name: string;
  size?: number;
}) {
  const [failed, setFailed] = useState(false);
  const fallback = (
    <span
      aria-hidden="true"
      className="flex shrink-0 items-center justify-center rounded-[8px] border border-[var(--separator)] bg-surface-secondary text-muted"
      style={{ height: size, width: size }}
    >
      <span className="text-[15px] font-semibold">{name.slice(0, 1)}</span>
    </span>
  );

  if (!domain || failed) return fallback;

  return (
    <img
      alt=""
      aria-hidden="true"
      className="shrink-0 rounded-[8px] border border-[var(--separator)] bg-background object-contain p-[4px]"
      height={size}
      loading="lazy"
      onError={() => setFailed(true)}
      src={`https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=64`}
      width={size}
    />
  );
}
