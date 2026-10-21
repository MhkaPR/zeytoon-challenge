import localFont from "next/font/local";

/**
 * Self-hosted fonts (no external Google Fonts dependency, per the in-Iran hosting principle).
 *
 * Vazirmatn covers Persian/Arabic script; Geist covers Latin text, numerals, and code.
 */
export const vazirmatn = localFont({
  src: [
    {
      path: "../src/fonts/vazirmatn-arabic-wght-normal.woff2",
      weight: "100 900",
      style: "normal",
    },
    {
      path: "../src/fonts/vazirmatn-latin-wght-normal.woff2",
      weight: "100 900",
      style: "normal",
    },
  ],
  variable: "--font-vazirmatn",
  display: "swap",
});

export const geistSans = localFont({
  src: [
    {
      path: "../src/fonts/Geist-Variable.woff2",
      weight: "100 900",
      style: "normal",
    },
  ],
  variable: "--font-geist-sans",
  display: "swap",
});

export const geistMono = localFont({
  src: [
    {
      path: "../src/fonts/GeistMono-Variable.woff2",
      weight: "100 900",
      style: "normal",
    },
  ],
  variable: "--font-geist-mono",
  display: "swap",
});
