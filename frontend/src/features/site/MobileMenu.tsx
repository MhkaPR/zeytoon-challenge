"use client";

import { Button, Drawer } from "@heroui/react";
import { Menu } from "lucide-react";
import NextLink from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { LoginButton } from "@/src/features/auth/LoginButton";
import { useSession } from "@/src/features/auth/SessionProvider";
import { UserMenuPanel } from "@/src/features/auth/UserMenuPanel";
import { strings } from "@/src/lib/i18n/strings";

import { Logo } from "./Logo";
import { NAV_ITEMS } from "./navItems";

/**
 * Mobile navigation: a menu button (rendered on the left of the header in RTL) that opens a
 * right-side drawer holding the site links plus the account actions. On desktop this renders
 * nothing — ``SiteMenu`` shows the inline links instead (requirement: mobile header layout).
 */
export function MobileMenu() {
  const pathname = usePathname();
  const { identity, isAuthenticated } = useSession();
  const [open, setOpen] = useState(false);

  return (
    <div className="md:hidden">
      <Drawer isOpen={open} onOpenChange={setOpen}>
        <Button
          aria-label={strings.menuOpen}
          isIconOnly
          onPress={() => setOpen(true)}
          variant="ghost"
        >
          <Menu className="size-5" />
        </Button>
        <Drawer.Backdrop>
          <Drawer.Content placement="right">
            <Drawer.Dialog aria-label={strings.menuTitle} className="w-[300px] max-w-[85vw]">
              <Drawer.CloseTrigger />
              <Drawer.Header>
                <Logo />
              </Drawer.Header>
              <Drawer.Body className="flex flex-col gap-[4px]">
                <nav aria-label={strings.menuTitle}>
                  <ul className="flex flex-col">
                    {NAV_ITEMS.map((item) => (
                      <li key={item.href}>
                        <NextLink
                          aria-current={pathname === item.href ? "page" : undefined}
                          className="flex items-center rounded-[var(--radius)] px-[12px] py-[12px] text-[15px] font-medium text-foreground transition-colors hover:bg-surface-secondary aria-[current=page]:text-accent"
                          href={item.href}
                          onClick={() => setOpen(false)}
                        >
                          {item.label}
                        </NextLink>
                      </li>
                    ))}
                  </ul>
                </nav>
              </Drawer.Body>
              <Drawer.Footer className="flex flex-col gap-[8px]">
                {identity !== null &&
                  (isAuthenticated ? (
                    <UserMenuPanel onNavigate={() => setOpen(false)} />
                  ) : (
                    <LoginButton onPress={() => setOpen(false)} variant="menu" />
                  ))}
              </Drawer.Footer>
            </Drawer.Dialog>
          </Drawer.Content>
        </Drawer.Backdrop>
      </Drawer>
    </div>
  );
}
