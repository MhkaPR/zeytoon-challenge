"use client";

import { Button } from "@heroui/react";
import NextLink from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

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
            <NextLink
              href={item.href}
              aria-current={pathname === item.href ? "page" : undefined}
              className="text-[14px] font-medium text-foreground hover:text-accent aria-[current=page]:text-accent"
            >
              {item.label}
            </NextLink>
          </li>
        ))}
      </ul>

      {/* Mobile: the whole menu is a single disclosure button. */}
      <div className="md:hidden">
        <Button
          aria-expanded={open}
          aria-label={open ? strings.menuClose : strings.menuOpen}
          isIconOnly
          onPress={() => setOpen((value) => !value)}
          variant="ghost"
        >
          <span aria-hidden>{open ? "✕" : "☰"}</span>
        </Button>
        {open && (
          <ul className="absolute inset-inline-start-0 top-full z-10 mt-[8px] flex w-full flex-col gap-[8px] bg-surface p-[16px] shadow-overlay">
            {ITEMS.map((item) => (
              <li key={item.href}>
                <NextLink
                  href={item.href}
                  onClick={() => setOpen(false)}
                  aria-current={pathname === item.href ? "page" : undefined}
                  className="block py-[4px] text-[14px] font-medium text-foreground hover:text-accent aria-[current=page]:text-accent"
                >
                  {item.label}
                </NextLink>
              </li>
            ))}
            {/* Login becomes a plain menu item on mobile because there is no room. */}
            <li>
              <NextLink
                className="block py-[4px] text-[14px] font-medium text-accent"
                href="/login"
                onClick={() => setOpen(false)}
              >
                {strings.login}
              </NextLink>
            </li>
          </ul>
        )}
      </div>
    </>
  );
}
