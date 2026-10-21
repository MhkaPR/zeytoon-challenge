"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Card, DisplayHero } from "@/src/components/ui";
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
      <Card variant="featured" className="w-full max-w-sm p-[32px]">
        <DisplayHero className="mb-[32px] text-[40px]">{strings.login}</DisplayHero>
        <LoginForm onSuccess={(redirectTo) => router.replace(redirectTo || "/")} />
      </Card>
    </main>
  );
}
