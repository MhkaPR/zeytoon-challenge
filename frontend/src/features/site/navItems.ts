import { strings } from "@/src/lib/i18n/strings";

/** Primary site navigation, shared by the desktop links and the mobile drawer. */
export const NAV_ITEMS = [
  { href: "/", label: strings.navMainPage },
  { href: "/companies", label: strings.navCompanies },
  { href: "/about", label: strings.navAboutUs },
] as const;
