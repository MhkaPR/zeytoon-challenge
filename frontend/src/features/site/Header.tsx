"use client";

import { useEffect, useState } from "react";

import { LoginButton } from "@/src/features/auth/LoginButton";
import { useSession } from "@/src/features/auth/SessionProvider";
import { UserMenu } from "@/src/features/auth/UserMenu";
import { Logo } from "./Logo";
import { MobileMenu } from "./MobileMenu";
import { SiteMenu } from "./SiteMenu";

/**
 * Sticky site header. Desktop: logo, inline links, and the account action. Mobile: the menu
 * button on the left, the wordmark centered, and the account action (login button or the
 * user's phone number) on the right so it is always reachable without opening the menu.
 */
export function Header() {
  const [scrolled, setScrolled] = useState(false);
  const { identity, isAuthenticated } = useSession();
  // Render nothing auth-related until the identity resolves to avoid a login/user-menu flash.
  const authReady = identity !== null;

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 0);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-20 bg-background ${scrolled ? "shadow-surface" : ""}`}
    >
      <div className="relative mx-auto grid w-full max-w-[1200px] grid-cols-[auto_1fr_auto] items-center gap-[12px] px-[16px] py-[12px] sm:px-[24px] md:flex md:gap-[32px] md:px-[32px] md:py-[16px]">
        {/* Mobile: menu button first (left in RTL). Desktop: hidden. */}
        <div className="order-1 justify-self-start">
          <MobileMenu />
        </div>

        {/* Brand: centered on mobile, leading on desktop. */}
        <Logo className="order-2 justify-self-center md:order-1 md:justify-self-start" />

        {/* Desktop links, just after the brand. */}
        <div className="hidden md:order-2 md:block md:ms-auto">
          <SiteMenu />
        </div>

        {/* The one call to action — login, or the user's account. Always on the right. */}
        <div className="order-3 flex shrink-0 items-center justify-self-end">
          {authReady && (isAuthenticated ? <UserMenu /> : <LoginButton />)}
        </div>
      </div>
    </header>
  );
}
