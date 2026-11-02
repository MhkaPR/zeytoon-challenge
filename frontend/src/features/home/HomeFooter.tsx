import { Link, Separator, Typography } from "@heroui/react";
import NextLink from "next/link";

import { footerLinkGroups, strings } from "@/src/lib/i18n/strings";

const SOCIAL_LINKS = [
  { label: strings.footerSocialInstagram, href: "https://instagram.com" },
  { label: strings.footerSocialTelegram, href: "https://telegram.org" },
  { label: strings.footerSocialLinkedin, href: "https://linkedin.com" },
  { label: strings.footerSocialGithub, href: "https://github.com" },
] as const;

/**
 * Site footer: quick links, legal information, contact details, and social links, plus the
 * copyright line. Multi-column on desktop and stacked on mobile (DESIGN.md §9).
 */
export function HomeFooter() {
  return (
    <footer className="w-full">
      <Separator />
      <div className="mx-auto grid w-full max-w-[1200px] grid-cols-1 gap-[32px] px-[32px] py-[48px] sm:grid-cols-2 lg:grid-cols-4">
        <div className="flex flex-col gap-[8px]">
          <Typography className="text-[20px] font-semibold">{strings.appName}</Typography>
          <Typography className="leading-[1.8]" color="muted" type="body-sm">
            {strings.footerAbout}
          </Typography>
        </div>

        {footerLinkGroups.map((group) => (
          <nav aria-label={group.title} className="flex flex-col gap-[8px]" key={group.title}>
            <Typography className="font-semibold" type="body-sm">
              {group.title}
            </Typography>
            <ul className="flex flex-col gap-[6px]">
              {group.links.map((link) => (
                <li key={link.label}>
                  <NextLink className="text-[14px]" href={link.href}>
                    {link.label}
                  </NextLink>
                </li>
              ))}
            </ul>
          </nav>
        ))}

        <div className="flex flex-col gap-[8px]">
          <Typography className="font-semibold" type="body-sm">
            {strings.footerContactTitle}
          </Typography>
          <Link className="text-[14px]" href={`mailto:${strings.footerEmail}`}>
            {strings.footerEmail}
          </Link>
          <Typography className="text-[14px]" color="muted" type="body-sm">
            {strings.footerPhone}
          </Typography>
          <Typography className="text-[14px]" color="muted" type="body-sm">
            {strings.footerAddress}
          </Typography>
        </div>

        <div className="flex flex-col gap-[8px]">
          <Typography className="font-semibold" type="body-sm">
            {strings.footerSocialTitle}
          </Typography>
          <ul className="flex flex-row flex-wrap gap-[12px]">
            {SOCIAL_LINKS.map((link) => (
              <li key={link.label}>
                <Link className="text-[14px]" href={link.href} rel="noopener noreferrer" target="_blank">
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <Separator />
      <div className="mx-auto w-full max-w-[1200px] px-[32px] py-[24px]">
        <Typography className="text-[12px]" color="muted" type="body-xs">
          {strings.footerCopyright}
        </Typography>
      </div>
    </footer>
  );
}
