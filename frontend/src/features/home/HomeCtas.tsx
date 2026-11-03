import { useTranslations } from "next-intl";
import { buttonVariants } from "@heroui/styles";
import NextLink from "next/link";

/**
 * The two primary calls to action under the search box: browse the company directory, or
 * browse host/server plans (PAGES.yaml main page). Uses ``buttonVariants`` with
 * ``next/link`` so the olive primary/secondary styles apply to real navigation anchors.
 */
export function HomeCtas() {
  const ot = useTranslations();
  return (
    <div className="flex flex-row w-full flex-col items-stretch justify-center gap-[12px] sm:flex-row sm:items-center">
      <NextLink className={buttonVariants({ size: "lg" })} href="/companies">
        {ot("ctaViewCompanies")}
      </NextLink>
      <NextLink
        className={buttonVariants({ size: "lg", variant: "secondary" })}
        href="/search"
      >
        {ot("ctaViewHosts")}
      </NextLink>
    </div>
  );
}
