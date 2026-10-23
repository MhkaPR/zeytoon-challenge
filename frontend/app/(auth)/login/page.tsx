"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useLoginDialog } from "@/src/features/auth/LoginDialog";

/**
 * Legacy ``/login`` entry point. Login is a modal over the current page, so this route opens
 * the site-wide login dialog and lands the user back on the main page rather than rendering a
 * standalone login screen. The dialog state lives in the root layout, so it survives the
 * client-side redirect.
 */
export default function LoginPage() {
  const router = useRouter();
  const { open } = useLoginDialog();

  useEffect(() => {
    open();
    router.replace("/");
  }, [open, router]);

  return null;
}
