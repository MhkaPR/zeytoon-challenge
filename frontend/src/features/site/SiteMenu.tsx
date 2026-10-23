"use client";

import NextLink from "next/link";
import { usePathname } from "next/navigation";

import { strings } from "@/src/lib/i18n/strings";

import { NAV_ITEMS } from "./navItems";

/** Desktop primary navigation: the inline horizontal list of menu items (md and up). */
export function SiteMenu() {
  const pathname = usePathname();

  return (
    <nav aria-label={strings.navMainPage} className="hidden md:block">
      <ul className="flex flex-row items-center gap-[24px]">
        {NAV_ITEMS.map((item) => (
          <li key={item.href}>
            <NextLink
              aria-current={pathname === item.href ? "page" : undefined}
              className="text-[14px] font-medium text-foreground transition-colors hover:text-accent aria-[current=page]:text-accent"
              href={item.href}
            >
              {item.label}
            </NextLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
