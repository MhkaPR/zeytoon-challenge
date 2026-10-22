"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/src/components/ui";
import { strings } from "@/src/lib/i18n/strings";
import { Logo } from "./Logo";
import { SiteMenu } from "./SiteMenu";

/**
 * Sticky site header: logo, menu (mobile-collapsible), and the login action. The login
 * button is hidden on narrow screens where it collapses into a menu item (PAGES.yaml).
 */
export function Header() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 0);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-20 bg-[var(--ds-white)] ${
        scrolled ? "shadow-[var(--ds-shadow-subtle)]" : ""
      }`}
    >
      <div className="relative mx-auto flex w-full max-w-[1200px] flex-row items-center justify-between gap-[16px] px-[32px] py-[16px]">
        <Logo />
        <nav aria-label={strings.navMainPage} className="flex flex-row items-center gap-[16px]">
          <SiteMenu />
          <Link href="/login" className="hidden md:inline-flex">
            <Button variant="primary" size="sm">
              {strings.login}
            </Button>
          </Link>
        </nav>
      </div>
    </header>
  );
}
