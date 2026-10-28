"use client";

import { Button, Separator, Typography } from "@heroui/react";
import { Building2, ClipboardCheck, LogOut } from "lucide-react";
import NextLink from "next/link";
import { useRouter } from "next/navigation";

import { opsStrings, strings } from "@/src/lib/i18n/strings";
import { identityRole, isOperatorRole } from "@/src/lib/session";

import { useSession } from "./SessionProvider";

/**
 * The account block shown inside the mobile drawer: the user's recognizable masked phone
 * number followed by "my companies" and "logout". Mirrors the desktop user menu.
 */
export function UserMenuPanel({ onNavigate }: { onNavigate?: () => void }) {
  const router = useRouter();
  const { identity, signOut } = useSession();

  return (
    <div className="flex w-full flex-col gap-[12px]">
      <div className="flex flex-col gap-[2px]">
        <Typography className="text-[12px]" color="muted">
          {strings.userMenuLabel}
        </Typography>
        <Typography className="text-[15px] font-medium">
          {identity?.user?.phone ?? strings.userMenuLabel}
        </Typography>
      </div>
      <Separator />
      <NextLink
        className="flex items-center gap-[8px] rounded-[var(--radius)] px-[12px] py-[10px] text-[15px] font-medium text-foreground transition-colors hover:bg-surface-secondary"
        href="/panel"
        onClick={() => onNavigate?.()}
      >
        <Building2 className="size-4 shrink-0 text-muted" />
        {strings.myCompanies}
      </NextLink>
      {isOperatorRole(identityRole(identity)) && (
        <NextLink
          className="flex items-center gap-[8px] rounded-[var(--radius)] px-[12px] py-[10px] text-[15px] font-medium text-foreground transition-colors hover:bg-surface-secondary"
          href="/ops"
          onClick={() => onNavigate?.()}
        >
          <ClipboardCheck className="size-4 shrink-0 text-muted" />
          {opsStrings.console}
        </NextLink>
      )}
      <Button
        className="justify-start gap-[8px] text-danger"
        onPress={async () => {
          onNavigate?.();
          await signOut();
          router.push("/");
        }}
        variant="ghost"
      >
        <LogOut className="size-4 shrink-0" />
        {strings.logout}
      </Button>
    </div>
  );
}
