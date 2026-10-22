import type { Metadata } from "next";

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
 */
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="fa"
      dir="rtl"
      className={`${vazirmatn.variable} ${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-[var(--ds-white)] text-[var(--ds-ink)]">
        {children}
      </body>
    </html>
  );
}
