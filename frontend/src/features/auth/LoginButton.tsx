"use client";

import { buttonVariants } from "@heroui/styles";
import { Button } from "@heroui/react";

import { strings } from "@/src/lib/i18n/strings";

import { useLoginDialog } from "./LoginDialog";

/**
 * Opens the site-wide login modal. ``variant="header"`` renders the button-styled desktop
 * action; ``variant="menu"`` renders a plain link-like row so it can live inside the mobile
 * menu without displacing the layout (PAGES.yaml header spec).
 */
export function LoginButton({
  variant = "header",
  onPress,
}: {
  variant?: "header" | "menu";
  onPress?: () => void;
}) {
  const { open } = useLoginDialog();

  if (variant === "menu") {
    return (
      <Button
        className="h-auto justify-start p-0 text-[14px] font-medium text-accent"
        onPress={() => {
          onPress?.();
          open();
        }}
        variant="ghost"
      >
        {strings.login}
      </Button>
    );
  }

  return (
    <Button
      className={buttonVariants({ size: "sm" })}
      onPress={() => {
        onPress?.();
        open();
      }}
    >
      {strings.login}
    </Button>
  );
}
