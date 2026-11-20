import { getTranslations } from "next-intl/server";
import NextLink from "next/link";

import type { SiteConfig } from "@/src/lib/config/siteConfig";
import { Link, Separator, Typography } from "@/src/features/ui/heroUi";

type FooterLinkGroup = {
  title: string;
  links: Array<{ label: string; href: string }>;
};

/**
 * Site footer: quick links, legal information, contact details, and social links, plus the
 * copyright line. Multi-column on desktop and stacked on mobile (DESIGN.md §9).
 */
export async function HomeFooter({ config }: { config: SiteConfig }) {
  const ot = await getTranslations();
  const footerLinkGroups = ot.raw("footerLinkGroups") as FooterLinkGroup[];
  const socialLinks = [
    { label: ot("footerSocialInstagram"), href: config.social.instagram },
    { label: ot("footerSocialTelegram"), href: config.social.telegram },
    { label: ot("footerSocialLinkedin"), href: config.social.linkedin },
    { label: ot("footerSocialGithub"), href: config.social.github },
  ];

  return (
    <footer className="w-full">
      <Separator />
      <div className="mx-auto grid w-full max-w-[1200px] grid-cols-1 gap-[32px] px-[32px] py-[48px] sm:grid-cols-2 lg:grid-cols-4">
        <div className="flex flex-col gap-[8px]">
          <Typography className="text-[20px] font-semibold">{ot("appName")}</Typography>
          <Typography className="leading-[1.8]" color="muted" type="body-sm">
            {ot("footerAbout")}
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
            {ot("footerContactTitle")}
          </Typography>
          <Link className="text-[14px]" href={`mailto:${config.contact.email}`}>
            {config.contact.email}
          </Link>
          <Typography className="text-[14px]" color="muted" type="body-sm">
            {config.contact.phone}
          </Typography>
          <Typography className="text-[14px]" color="muted" type="body-sm">
            {config.contact.address}
          </Typography>
        </div>

        <div className="flex flex-col gap-[8px]">
          <Typography className="font-semibold" type="body-sm">
            {ot("footerSocialTitle")}
          </Typography>
          <ul className="flex flex-row flex-wrap gap-[12px]">
            {socialLinks.map((link) => (
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
          {ot("footerCopyright")}
        </Typography>
      </div>
    </footer>
  );
}
