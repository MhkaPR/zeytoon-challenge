"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { LoginForm } from "@/src/features/auth/LoginForm";
import { captureReturnUrl } from "@/src/features/auth/returnUrl";

export default function LoginPage() {
  const router = useRouter();

  useEffect(() => {
    captureReturnUrl();
  }, []);

  return (
    <main className="flex flex-1 items-center justify-center p-8">
      <div className="w-full max-w-sm">
        <h1 className="mb-6 text-2xl font-semibold tracking-tight">Log in</h1>
        <LoginForm onSuccess={(redirectTo) => router.replace(redirectTo || "/")} />
      </div>
    </main>
  );
}
