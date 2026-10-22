"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { Button } from "@/src/components/ui";
import { strings } from "@/src/lib/i18n/strings";

const ITEMS = [
  { href: "/", label: strings.navMainPage },
  { href: "/companies", label: strings.navCompanies },
  { href: "/about", label: strings.navAboutUs },
] as const;

/**
 * Primary navigation. On desktop the links render inline in the header; on mobile they
 * collapse into a single menu button. The login action is rendered separately by the
 * header so it can degrade to a menu item on narrow screens (PAGES.yaml header spec).
 */
export function SiteMenu() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Desktop: horizontal list of menu items. */}
      <ul className="hidden flex-row items-center gap-[16px] md:flex">
        {ITEMS.map((item) => (
          <li key={item.href}>
            <Link
              href={item.href}
              aria-current={pathname === item.href ? "page" : undefined}
              className="text-[14px] font-medium text-[var(--ds-ink)] hover:text-[var(--ds-olive-700)] aria-[current=page]:text-[var(--ds-olive-700)]"
            >
              {item.label}
            </Link>
          </li>
        ))}
      </ul>

      {/* Mobile: the whole menu is a single disclosure button. */}
      <div className="md:hidden">
        <Button
          variant="ghost"
          size="sm"
          aria-expanded={open}
          aria-label={open ? strings.menuClose : strings.menuOpen}
          onClick={() => setOpen((value) => !value)}
        >
          <span aria-hidden>{open ? "✕" : "☰"}</span>
        </Button>
        {open && (
          <ul className="absolute inset-inline-start-0 top-full z-10 mt-[8px] flex w-full flex-col gap-[8px] bg-[var(--ds-white)] p-[16px] shadow-[var(--ds-shadow-card)]">
            {ITEMS.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  onClick={() => setOpen(false)}
                  aria-current={pathname === item.href ? "page" : undefined}
                  className="block py-[4px] text-[14px] font-medium text-[var(--ds-ink)] hover:text-[var(--ds-olive-700)] aria-[current=page]:text-[var(--ds-olive-700)]"
                >
                  {item.label}
                </Link>
              </li>
            ))}
            {/* Login becomes a plain menu item on mobile because there is no room. */}
            <li>
              <Link
                href="/login"
                onClick={() => setOpen(false)}
                className="block py-[4px] text-[14px] font-medium text-[var(--ds-olive-700)]"
              >
                {strings.login}
              </Link>
            </li>
          </ul>
        )}
      </div>
    </>
  );
}
