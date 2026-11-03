import { useTranslations } from "next-intl";
import { Link, Separator, Typography } from "@heroui/react";
import NextLink from "next/link";


/**
 * Site footer: quick links, legal information, contact details, and social links, plus the
 * copyright line. Multi-column on desktop and stacked on mobile (DESIGN.md §9).
 */
export function HomeFooter() {
  const ot = useTranslations();
  const footerLinkGroups = ot.raw("footerLinkGroups") as Array<{ title: string; links: Array<{ label: string; href: string }> }>;
  const socialLinks = [
    { label: ot("footerSocialInstagram"), href: "https://instagram.com" },
    { label: ot("footerSocialTelegram"), href: "https://telegram.org" },
    { label: ot("footerSocialLinkedin"), href: "https://linkedin.com" },
    { label: ot("footerSocialGithub"), href: "https://github.com" },
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
          <Link className="text-[14px]" href={`mailto:${ot("footerEmail")}`}>
            {ot("footerEmail")}
          </Link>
          <Typography className="text-[14px]" color="muted" type="body-sm">
            {ot("footerPhone")}
          </Typography>
          <Typography className="text-[14px]" color="muted" type="body-sm">
            {ot("footerAddress")}
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
