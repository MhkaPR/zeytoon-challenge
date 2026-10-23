"use client";

import { Button, Dropdown, Label } from "@heroui/react";
import { Building2, ChevronDown, LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

import { strings } from "@/src/lib/i18n/strings";

import { useSession } from "./SessionProvider";

// The authenticated header action: the user's masked phone number opens a dropdown listing
// "my companies" and "logout". It replaces the login button once the session is authenticated.
export function UserMenu({ onNavigate }: { onNavigate?: () => void }) {
  const router = useRouter();
  const { identity, signOut } = useSession();
  const maskedPhone = identity?.user?.phone;

  async function handleAction(key: React.Key) {
    onNavigate?.();
    if (key === "companies") {
      router.push("/panel");
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
        <span className="font-medium text-foreground">{maskedPhone ?? strings.userMenuLabel}</span>
        <ChevronDown aria-hidden className="size-4 text-muted" />
      </Button>
      <Dropdown.Popover>
        <Dropdown.Menu onAction={handleAction}>
          <Dropdown.Item id="companies" textValue={strings.myCompanies}>
            <Building2 className="size-4 shrink-0 text-muted" />
            <Label>{strings.myCompanies}</Label>
          </Dropdown.Item>
          <Dropdown.Item id="logout" textValue={strings.logout} variant="danger">
            <LogOut className="size-4 shrink-0 text-danger" />
            <Label>{strings.logout}</Label>
          </Dropdown.Item>
        </Dropdown.Menu>
      </Dropdown.Popover>
    </Dropdown>
  );
}
