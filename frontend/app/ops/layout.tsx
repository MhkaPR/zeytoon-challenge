"use client";

import { useTranslations } from "next-intl";
import { Skeleton, Typography } from "@heroui/react";
import { ClipboardCheck, Globe } from "lucide-react";
import NextLink from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Suspense, useEffect } from "react";

import { useSession } from "@/src/features/auth/SessionProvider";
import { LoginButton } from "@/src/features/auth/LoginButton";
import { identityRole, isOperatorRole } from "@/src/lib/session";

const NAV = [
  { href: "/ops", labelKey: "navApprovals", icon: ClipboardCheck },
  { href: "/ops/sites", labelKey: "navSites", icon: Globe },
] as const;

/**
 * Operator-only shell. ``usePathname`` is dynamic, so the shell lives inside a Suspense
 * boundary; otherwise Next's cacheComponents prerender fails for dynamic routes such as
 * ``/ops/sites/[siteId]``.
 */
export default function OpsLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense
      fallback={
        <main className="mx-auto w-full max-w-[1100px] flex-1 px-[16px] py-[40px]">
          <Skeleton className="h-[200px] rounded-[var(--radius)]" />
        </main>
      }
    >
      <OpsShell>{children}</OpsShell>
    </Suspense>
  );
}

function OpsShell({ children }: { children: React.ReactNode }) {
  const ot = useTranslations();
  const { identity } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const role = identityRole(identity);
  const isOperator = isOperatorRole(role);

  useEffect(() => {
    if (identity?.authenticated && !isOperator) {
      router.replace("/panel");
    }
  }, [identity, isOperator, router]);

  if (identity === null) {
    return (
      <main className="mx-auto w-full max-w-[1100px] flex-1 px-[16px] py-[40px]">
        <Skeleton className="h-[200px] rounded-[var(--radius)]" />
      </main>
    );
  }

  if (!identity.authenticated) {
    return (
      <main className="mx-auto flex w-full max-w-[1100px] flex-1 flex-col gap-[16px] px-[16px] py-[40px]">
        <Typography className="text-[20px] font-semibold" type="h2">
          {ot("console")}
        </Typography>
        <Typography className="text-[14px]">{ot("adminOnly")}</Typography>
        <div>
          <LoginButton />
        </div>
      </main>
    );
  }

  if (!isOperator) {
    return (
      <main className="mx-auto w-full max-w-[1100px] flex-1 px-[16px] py-[40px]">
        <Typography role="alert">{ot("adminOnly")}</Typography>
      </main>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-1 flex-col gap-[24px] px-[16px] py-[32px] sm:px-[24px] md:px-[32px]">
      <header className="flex flex-col gap-[16px] border-b border-[var(--ds-border)] pb-[16px]">
        <div className="flex flex-col gap-[4px]">
          <Typography className="text-[24px] font-semibold sm:text-[30px]" type="h1">
            {ot("console")}
          </Typography>
          <Typography className="text-[13px] text-muted">{ot("consoleSubtitle")}</Typography>
        </div>
        <nav aria-label={ot("console")}>
          <ul className="flex flex-wrap gap-[8px]">
            {NAV.map((item) => {
              const Icon = item.icon;
              const active =
                item.href === "/ops"
                  ? pathname === "/ops"
                  : pathname?.startsWith(item.href);
              return (
                <li key={item.href}>
                  <NextLink
                    aria-current={active ? "page" : undefined}
                    className={`flex items-center gap-[6px] rounded-[var(--radius)] px-[12px] py-[8px] text-[14px] font-medium transition-colors ${
                      active
                        ? "bg-accent text-accent-foreground"
                        : "text-muted hover:bg-surface-secondary"
                    }`}
                    href={item.href}
                  >
                    <Icon aria-hidden className="size-4" />
                    {ot(item.labelKey)}
                  </NextLink>
                </li>
              );
            })}
          </ul>
        </nav>
      </header>
      {children}
    </div>
  );
}
