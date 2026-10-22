"use client";

import { Card, Typography } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { LoginForm } from "@/src/features/auth/LoginForm";
import { captureReturnUrl } from "@/src/features/auth/returnUrl";
import { strings } from "@/src/lib/i18n/strings";

export default function LoginPage() {
  const router = useRouter();

  useEffect(() => {
    captureReturnUrl();
  }, []);

  return (
    <main className="flex flex-1 items-center justify-center p-[32px]">
      <Card className="w-full max-w-sm p-[32px]" variant="tertiary">
        <Typography className="mb-[32px] text-[40px] font-semibold" type="h1">
          {strings.login}
        </Typography>
        <LoginForm onSuccess={(redirectTo) => router.replace(redirectTo || "/")} />
      </Card>
    </main>
  );
}
