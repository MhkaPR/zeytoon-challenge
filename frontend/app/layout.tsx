import type { Metadata } from "next";

import { LoginDialogProvider } from "@/src/features/auth/LoginDialog";
import { SessionProvider } from "@/src/features/auth/SessionProvider";
import { Header } from "@/src/features/site/Header";

import { geistMono, geistSans, vazirmatn } from "./fonts";
import "./globals.css";

export const metadata: Metadata = {
  title: "ترب — مقایسه پلنهای میزبانی و سرور",
  description: "جستوجو و مقایسه پلنهای میزبانی و سرور میان ارائهدهندگان مختلف.",
};

/**
 * Root layout. The product is Persian-first and fully RTL: ``lang="fa"`` and ``dir="rtl"``
 * are set on the document. Fonts are self-hosted (Vazirmatn for Persian, Geist for Latin
 * text and code) so there is no external Google Fonts dependency.
 *
 * The site header and the login modal live here so every page shares the same chrome and the
 * login experience is a modal over the current page instead of a separate route
 * (requirement: header on nearly all pages, login as a modal on main pages).
 */
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="fa"
      dir="rtl"
      className={`${vazirmatn.variable} ${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-[var(--ds-white)] text-[var(--ds-ink)]">
        <SessionProvider>
          <LoginDialogProvider>
            <Header />
            {children}
          </LoginDialogProvider>
        </SessionProvider>
      </body>
    </html>
  );
}
