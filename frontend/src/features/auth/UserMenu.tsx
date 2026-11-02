"use client";

import { useTranslations } from "next-intl";
import { Button, Dropdown, Label } from "@heroui/react";
import { Building2, ChevronDown, ClipboardCheck, LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

import { identityRole, isOperatorRole } from "@/src/lib/session";

import { useSession } from "./SessionProvider";

// The authenticated header action: the user's masked phone number opens a dropdown listing
// "my companies" and "logout". It replaces the login button once the session is authenticated.
export function UserMenu({ onNavigate }: { onNavigate?: () => void }) {
  const t = useTranslations("common");
const ot = useTranslations("ops");
  const router = useRouter();
  const { identity, signOut } = useSession();
  const phone = identity?.user?.phone;

  async function handleAction(key: React.Key) {
    onNavigate?.();
    if (key === "companies") {
      router.push("/panel");
      return;
    }
    if (key === "ops") {
      router.push("/ops");
      return;
    }
    if (key === "logout") {
      await signOut();
      router.push("/");
    }
  }

  return (
    <Dropdown>
      <Button className="gap-[6px]" variant="ghost">
        <span className="font-medium text-foreground">{phone ?? t("userMenuLabel")}</span>
        <ChevronDown aria-hidden className="size-4 text-muted" />
      </Button>
      <Dropdown.Popover>
        <Dropdown.Menu onAction={handleAction}>
          <Dropdown.Item id="companies" textValue={t("myCompanies")}>
            <Building2 className="size-4 shrink-0 text-muted" />
            <Label>{t("myCompanies")}</Label>
          </Dropdown.Item>
          {isOperatorRole(identityRole(identity)) && (
            <Dropdown.Item id="ops" textValue={ot("console")}>
              <ClipboardCheck className="size-4 shrink-0 text-muted" />
              <Label>{ot("console")}</Label>
            </Dropdown.Item>
          )}
          <Dropdown.Item id="logout" textValue={t("logout")} variant="danger">
            <LogOut className="size-4 shrink-0 text-danger" />
            <Label>{t("logout")}</Label>
          </Dropdown.Item>
        </Dropdown.Menu>
      </Dropdown.Popover>
    </Dropdown>
  );
}
