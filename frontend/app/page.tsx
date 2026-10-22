import Link from "next/link";

import {
  Badge,
  Body,
  BodyLarge,
  Button,
  Card,
  CardTitle,
  DisplayHero,
  MonoLabel,
  SectionHeading,
} from "@/src/components/ui";
import { strings } from "@/src/lib/i18n/strings";

/**
 * Landing page. Demonstrates the DESIGN.md system: RTL Persian layout, white canvas, black
 * text with olive accents, shadow-as-border cards, and generous whitespace.
 */
export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-[80px] px-[32px] py-[80px]">
      <section className="flex flex-col items-start gap-[16px]">
        <MonoLabel>{strings.appName}</MonoLabel>
        <DisplayHero>{strings.heroTitle}</DisplayHero>
        <BodyLarge className="max-w-[640px]">{strings.heroSubtitle}</BodyLarge>
        <div className="flex flex-row gap-[8px]">
          <Link href="/login">
            <Button variant="primary">{strings.login}</Button>
          </Link>
          <Button variant="secondary">{strings.comparePlans}</Button>
        </div>
      </section>

      <section className="flex flex-col gap-[32px]">
        <SectionHeading>{strings.howItWorks}</SectionHeading>
        <div className="grid grid-cols-1 gap-[32px] md:grid-cols-3">
          <Card variant="featured">
            <MonoLabel className="text-[var(--develop-text)]">{strings.stepDevelop}</MonoLabel>
            <CardTitle className="mt-[8px]">{strings.stepDevelopTitle}</CardTitle>
            <Body className="mt-[8px]">{strings.stepDevelopBody}</Body>
          </Card>
          <Card variant="featured">
            <MonoLabel className="text-[var(--preview-text)]">{strings.stepPreview}</MonoLabel>
            <CardTitle className="mt-[8px]">{strings.stepPreviewTitle}</CardTitle>
            <Body className="mt-[8px]">{strings.stepPreviewBody}</Body>
          </Card>
          <Card variant="featured">
            <MonoLabel className="text-[var(--ship-text)]">{strings.stepShip}</MonoLabel>
            <CardTitle className="mt-[8px]">{strings.stepShipTitle}</CardTitle>
            <Body className="mt-[8px]">{strings.stepShipBody}</Body>
          </Card>
        </div>
      </section>

      <section className="flex flex-col gap-[16px]">
        <SectionHeading>{strings.builtForScale}</SectionHeading>
        <div className="flex flex-row gap-[8px]">
          <Badge>{strings.badgeThroughput}</Badge>
          <Badge>{strings.badgeFreshness}</Badge>
          <Badge>{strings.badgeLocalIndex}</Badge>
        </div>
      </section>
    </main>
  );
}
